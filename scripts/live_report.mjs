/** Public CI evidence intentionally excludes arbitrary data returned by HA. */
const KNOWN_CHECKS = Object.freeze([
  "onboarding",
  "ha_running_before_configuration",
  "fresh_manifest_dependency_installation",
  "paged_import_comparison_preserves_pending_data",
  "mosque_config_flow",
  "authenticated_csv_upload_mapping_review_approval",
  "27_sensors",
  "native_calendar_approved_instant_events",
  "automatic_resource_registration",
  "dashboard_configuration",
  "confirmed_ramadan",
  "iftar_fallback",
  "taraweeh_text_without_timestamp",
  "two_mosque_dashboard_cards",
  "two_mosques_independent_approval",
  "entry_remove_readd_clears_only_own_storage",
  "no_stale_readded_entities",
  "resource_deduplication_after_readd",
  "official_backup_archive_restored_into_second_disposable_config",
  "calendar_excludes_pending_proposal",
  "calendar_ids_survive_restart_and_rejection",
  "restart_approved_pending_ramadan_and_ids",
  "rejection_preserves_approved",
  "resource_deduplication",
  "real_frontend_card_picker_editor",
  "light_dark_theme",
  "keyboard_title_and_focus",
  "phone_tablet_viewports",
  "text_scale"
]);

/** Project only fixed test names, boolean attestations and validated provenance. */
export function publicSmokeReport(report) {
  const result = {
    ha_version: report.ha_version,
    status: report.status === "passed" ? "passed" : "failed",
    dependency_preloaded: report.dependency_preloaded === true,
    custom_ca_bundle: report.custom_ca_bundle === true,
    checks: KNOWN_CHECKS.filter(name => report.checks?.includes(name)),
    dependency: report.dependency ? {
      baseline_absent: report.dependency.before_version === null && report.dependency.before_module_version === null,
      installed_metadata_matches_manifest: report.dependency.installed_version === report.dependency.expected_version,
      imported_module_matches_manifest: report.dependency.installed_module_version === report.dependency.expected_version,
      fresh_install_verified: report.dependency.fresh_install_verified === true,
    } : null,
    restart_fajr: report.restart_fajr ? {
      present: report.restart_fajr.present === true,
      available: report.restart_fajr.available === true,
      matches_approved: report.restart_fajr.matches_approved === true,
    } : null,
    browser_completed: Boolean(report.browser),
    working_tree_dirty: report.working_tree_dirty === true,
  };
  // The SHA is obtained from the local Git checkout, not HA. Verify its shape.
  if (typeof report.source_commit === "string" && /^[0-9a-f]{40}$/.test(report.source_commit)) {
    result.source_commit = report.source_commit;
  }
  // HTTP error messages may contain remote values or credentials.
  if (result.status === "failed") result.failure = "See GitHub Actions job logs";
  return result;
}
