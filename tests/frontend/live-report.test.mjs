import assert from "node:assert/strict";
import test from "node:test";
import {publicSmokeReport} from "../../scripts/live_report.mjs";

test("public report retains checked results and provenance", () => {
  const safe = publicSmokeReport({
    ha_version: "2026.10.3", status: "passed",
    checks: ["onboarding", "26_sensors", "real_frontend_card_picker_editor"],
    dependency: {
      expected_version: "6.21.1", before_version: null, before_module_version: null,
      installed_version: "6.21.1", installed_module_version: "6.21.1",
      fresh_install_verified: true,
    },
    restart_fajr: {present: true, available: true, matches_approved: true},
    browser: {picker: true}, source_commit: "f".repeat(40),
  });
  assert.deepEqual(safe.checks, ["onboarding", "26_sensors", "real_frontend_card_picker_editor"]);
  assert.equal(safe.status, "passed");
  assert.equal(safe.browser_completed, true);
  assert.equal(safe.dependency.fresh_install_verified, true);
  assert.equal(safe.dependency.installed_metadata_matches_manifest, true);
  assert.equal(safe.restart_fajr.matches_approved, true);
  assert.equal(safe.source_commit, "f".repeat(40));
  assert.equal(safe.failure, undefined);
});

test("public report drops untrusted text, diagnostics and invalid provenance", () => {
  const attacker = "SENSITIVE_REMOTE_TOKEN_<script>exploit</script>";
  const safe = publicSmokeReport({
    ha_version: "2026.10.3", status: "failed",
    checks: [attacker, "onboarding", attacker, "26_sensors"],
    failure: attacker, startup_diagnostics: {container: {status: attacker}},
    dependency: {
      before_version: attacker, before_module_version: attacker,
      expected_version: "6.21.1", installed_version: attacker,
      installed_module_version: attacker, fresh_install_verified: attacker,
    },
    restart_fajr: {present: attacker, available: attacker, matches_approved: attacker},
    browser: {url: attacker, secret: attacker},
    source_commit: attacker, image_id: attacker, integration_version: attacker,
  });
  assert.equal(JSON.stringify(safe).includes(attacker), false);
  assert.deepEqual(safe.checks, ["onboarding", "26_sensors"]);
  assert.equal(safe.failure, "See GitHub Actions job logs");
  assert.equal(safe.dependency.fresh_install_verified, false);
  assert.equal(safe.dependency.installed_metadata_matches_manifest, false);
  assert.equal(safe.restart_fajr.present, false);
  assert.equal(safe.source_commit, undefined);
  assert.deepEqual(Object.keys(safe).sort(), [
    "browser_completed", "checks", "custom_ca_bundle", "dependency",
    "dependency_preloaded", "failure", "ha_version", "restart_fajr",
    "status", "working_tree_dirty",
  ]);
});

test("public report handles a pre-onboarding failure", () => {
  const safe = publicSmokeReport({ha_version: "2026.10.3", checks: []});
  assert.deepEqual(safe.checks, []);
  assert.equal(safe.status, "failed");
  assert.equal(safe.dependency, null);
  assert.equal(safe.restart_fajr, null);
  assert.equal(safe.browser_completed, false);
});
