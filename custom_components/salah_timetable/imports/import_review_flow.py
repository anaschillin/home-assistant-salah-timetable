"""Reusable staged-import review and comparison options-flow steps.

The concrete CSV/URL flow provides _coordinator() and the options-flow UI methods.
Staged IDs, approval baselines and the reload gate remain unchanged.
"""

import voluptuous as vol
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import selector

from ..domain.ramadan import RamadanSettings
from ..persistence.storage import RamadanApprovalError, ReviewChangedError
from .import_comparison import (
    DEFAULT_PAGE_SIZE,
    compare_import,
    comparison_overview,
    render_comparison_page,
)
from .import_preview import import_summary


class ImportReviewFlowMixin:
    """Review and compare approved-source changes without activating staged data."""

    def _review_source_context(self, candidate, coordinator):
        """Let source adapters validate the exact refreshed staged candidate."""
        return "", None

    async def _async_load_review_storage(self, coordinator, errors: dict) -> bool:
        """Reject decisions against unreadable disk state, without losing the preview."""
        try:
            await coordinator.storage.async_load()
        except OSError, HomeAssistantError, ValueError, TypeError, KeyError:
            errors["base"] = "save_failed"
            return False
        return True

    async def _async_apply_review_decision(self, coordinator, decision: str) -> bool:
        """Only explicit approval or rejection mutates the staged import."""
        if decision == "approve":
            if self._review_baseline is None:
                raise ReviewChangedError("A comparison must be shown first")
            await coordinator.storage.async_approve(
                self._review_stage_id,
                expected_baseline=self._review_baseline,
            )
            current = self._coordinator()
            if current is not None:
                await current.storage.async_load()
                await current.async_refresh()
                current.async_update_listeners()
            return True
        if decision == "reject":
            await coordinator.storage.async_reject(self._review_stage_id)
            coordinator.async_update_listeners()
            return True
        return False

    @staticmethod
    def _render_review_details(candidate, tables, settings, baseline, source_summary):
        """Build bounded user-visible comparison text outside the event loop."""
        comparison = compare_import(candidate, baseline.timetable, baseline.source)
        summary = import_summary(candidate, tables, settings)
        if source_summary:
            summary = source_summary + "\n\n" + summary
        return summary + "\n\n" + comparison_overview(comparison)

    async def async_step_review(self, user_input=None):
        coordinator = self._coordinator()
        if coordinator is None:
            return self.async_abort(reason="integration_not_loaded")
        errors = {}
        if not await self._async_load_review_storage(coordinator, errors):
            user_input = None
        if self._coordinator() is not coordinator:
            return self.async_abort(reason="integration_reloaded")
        staged = coordinator.storage.staged
        if staged is None:
            return self.async_abort(reason="no_pending_import")
        if self._review_runtime is None:
            self._review_runtime = coordinator
        elif self._review_runtime is not coordinator:
            return self.async_abort(reason="integration_reloaded")
        if self._review_stage_id is None:
            self._review_stage_id = staged.stage_id
        if self._review_stage_id != staged.stage_id:
            return self.async_abort(reason="stale_import")
        source_summary, source_error = self._review_source_context(
            staged.candidate, coordinator
        )
        if source_error is not None:
            errors["base"] = source_error
            if user_input is not None and user_input.get("decision") == "approve":
                user_input = None
        if user_input is not None:
            decision = user_input["decision"]
            if decision == "compare":
                self._review_page = 0
                self._review_canonical_only = False
                return await self.async_step_compare()
            try:
                applied = await self._async_apply_review_decision(coordinator, decision)
                if not applied:
                    errors["base"] = "invalid_import_decision"
            except ReviewChangedError:
                self._review_page = 0
                errors["base"] = "review_changed"
            except RamadanApprovalError:
                errors["base"] = "ramadan_conflict"
            except ValueError:
                return self.async_abort(reason="stale_import")
            except (
                OSError,
                HomeAssistantError,
            ):
                errors["base"] = "save_failed"
            else:
                if applied:
                    return self.async_create_entry(
                        title="", data=dict(self.config_entry.options)
                    )
        tables = coordinator.storage.timetables
        baseline = coordinator.storage.review_baseline(
            staged.candidate.timetable.timetable_id
        )
        settings = RamadanSettings.from_options(self.config_entry.options)

        summary = await self.hass.async_add_executor_job(
            self._render_review_details,
            staged.candidate,
            tables,
            settings,
            baseline,
            source_summary,
        )
        if self._coordinator() is not coordinator:
            return self.async_abort(reason="integration_reloaded")
        self._review_baseline = baseline
        return self.async_show_form(
            step_id="review",
            data_schema=vol.Schema(
                {
                    vol.Required("decision"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=["compare", "approve", "reject"],
                            translation_key="import_decision",
                        )
                    )
                }
            ),
            errors=errors,
            description_placeholders={
                "summary": f"Mosque timezone: {coordinator.zone.key}\n\n" + summary
            },
        )

    async def async_step_compare(self, user_input=None):
        """Page through pending-source differences without changing active data."""
        coordinator = self._coordinator()
        if coordinator is None:
            return self.async_abort(reason="integration_not_loaded")
        if self._review_runtime is not coordinator:
            return self.async_abort(reason="integration_reloaded")
        errors = {}
        if not await self._async_load_review_storage(coordinator, errors):
            user_input = None
        if self._coordinator() is not coordinator:
            return self.async_abort(reason="integration_reloaded")
        staged = coordinator.storage.staged
        if staged is None or staged.stage_id != self._review_stage_id:
            return self.async_abort(reason="stale_import")

        source_summary, source_error = self._review_source_context(
            staged.candidate, coordinator
        )
        if source_error is not None:
            errors["base"] = source_error
        baseline = coordinator.storage.review_baseline(
            staged.candidate.timetable.timetable_id
        )
        if self._review_baseline != baseline:
            self._review_page = 0
            errors.setdefault("base", "review_changed")
            user_input = None
        comparison = await self.hass.async_add_executor_job(
            compare_import, staged.candidate, baseline.timetable, baseline.source
        )
        if user_input is not None:
            action = user_input["action"]
            if action == "review":
                return await self.async_step_review()
            if action == "next":
                self._review_page += 1
            elif action == "previous":
                self._review_page -= 1
            elif action == "canonical":
                self._review_canonical_only = True
                self._review_page = 0
            elif action == "all":
                self._review_canonical_only = False
                self._review_page = 0
            else:
                errors["base"] = "invalid_import_decision"
        page_count = comparison.page_count(canonical_only=self._review_canonical_only)
        self._review_page = min(max(0, self._review_page), page_count - 1)
        options = ["review", "all" if self._review_canonical_only else "canonical"]
        if self._review_page > 0:
            options.append("previous")
        if self._review_page + 1 < page_count:
            options.append("next")
        detail = await self.hass.async_add_executor_job(
            render_comparison_page,
            comparison,
            self._review_page,
            DEFAULT_PAGE_SIZE,
            self._review_canonical_only,
        )
        if self._coordinator() is not coordinator:
            return self.async_abort(reason="integration_reloaded")
        self._review_baseline = baseline
        if source_summary:
            detail = source_summary + "\n\n" + detail
        return self.async_show_form(
            step_id="compare",
            data_schema=vol.Schema(
                {
                    vol.Required("action"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=options,
                            translation_key="import_compare_action",
                        )
                    )
                }
            ),
            errors=errors,
            description_placeholders={"detail": detail},
        )
