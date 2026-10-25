/** Opt-in smoke test against a disposable official Home Assistant container. */
import assert from "node:assert/strict";
import {spawn} from "node:child_process";
import {randomBytes} from "node:crypto";
import {mkdir, mkdtemp, readFile, rm, writeFile} from "node:fs/promises";
import {tmpdir} from "node:os";
import {createServer} from "node:net";
import {basename, join, resolve} from "node:path";
import {fileURLToPath} from "node:url";
import {waitForRunning, waitForEntry, pollUntil} from "./live_readiness.mjs";
import {dependencyEvidence, dependencyProbe} from "./live_dependency.mjs";
import {runBrowserSmoke} from "./live_browser.mjs";

const root = fileURLToPath(new URL("../", import.meta.url));
const options = {version: "2026.10.0", output: null, preload: false, requireFresh: false, caBundle: null, verifyBackupRestore: false};
for (let index = 2; index < process.argv.length; index++) {
  const argument = process.argv[index];
  if (argument === "--ha-version") options.version = process.argv[++index];
  else if (argument === "--output-dir") options.output = resolve(process.argv[++index]);
  else if (argument === "--require-fresh-dependency") options.requireFresh = true;
  else if (argument === "--ca-bundle") options.caBundle = resolve(process.argv[++index]);
  else if (argument === "--preload-pypdf") options.preload = true;
  else if (argument === "--verify-backup-restore") options.verifyBackupRestore = true;
  else if (argument === "--help") {
    console.log("node scripts/live_smoke.mjs [--ha-version 2026.10.0] [--output-dir PATH] [--preload-pypdf | --require-fresh-dependency] [--ca-bundle PATH] [--verify-backup-restore]\nRequires Docker, Node.js 24 and Chromium/Chrome (CHROME_BIN optional). Creates and removes its own container/configuration. --preload-pypdf explicitly supplies the locked local dependency instead of testing fresh installation. --require-fresh-dependency verifies absence before and the manifest-pinned import after setup. --ca-bundle mounts a trusted combined CA bundle read-only for dependency installation; TLS verification remains enabled.");
    process.exit(0);
  } else throw new Error(`Unknown argument: ${argument}`);
}
assert.match(options.version || "", /^\d{4}\.\d+\.\d+$/, "Use an explicit stable HA version");

assert.ok(!(options.preload && options.requireFresh), "Cannot require fresh installation while preloading pypdf");
const abort = new AbortController();
for (const signal of ["SIGINT", "SIGTERM"]) process.once(signal, () => abort.abort(new Error("Smoke test interrupted")));
const limit = setTimeout(() => abort.abort(new Error("Smoke test exceeded ten minutes")), 600000);
const pause = async milliseconds => { abort.signal.throwIfAborted(); await new Promise(resolve => setTimeout(resolve, milliseconds)); abort.signal.throwIfAborted(); };
// Docker can reassign an automatically published port on restart. Select an
// available host port first, then publish it explicitly so the test origin stays
// stable across HA restarts and frontend token refreshes.
const hostPort = await new Promise((resolve, reject) => {
  const server = createServer();
  server.once("error", reject);
  server.listen(0, "127.0.0.1", () => {
    const port = server.address().port;
    server.close(error => error ? reject(error) : resolve(port));
  });
});
const image = `ghcr.io/home-assistant/home-assistant:${options.version}`;
const container = `salah-live-${process.pid}-${randomBytes(5).toString("hex")}`;
const working = await mkdtemp(join(tmpdir(), "salah-ha-live-"));
const config = join(working, "config");
const report = {ha_version: options.version, dependency_preloaded: options.preload, checks: []};
let created = false;
let activeSocket;
let userRequested = false;

function command(executable, args, {cleanup = false} = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(executable, args, {stdio: ["ignore", "pipe", "pipe"], signal: cleanup ? AbortSignal.timeout(150000) : abort.signal});
    let stdout = ""; let stderr = "";
    child.stdout.on("data", value => { stdout = (stdout + value).slice(-65536); });
    child.stderr.on("data", value => { stderr = (stderr + value).slice(-4000); });
    child.once("error", reject);
    child.once("close", code => code === 0 ? resolve(stdout.trim()) : reject(new Error(`${executable} ${args[0]} failed (${code}): ${stderr}`)));
  });
}

let base; let tokens;
async function request(path, data, {auth = true, method = data === undefined ? "GET" : "POST", form = false} = {}) {
  const headers = auth && tokens ? {Authorization: `Bearer ${tokens.access_token}`} : {};
  if (data !== undefined && !form) headers["Content-Type"] = "application/json";
  const response = await fetch(base + path, {method, headers, body: data === undefined ? undefined : form ? data : JSON.stringify(data), signal: AbortSignal.any([abort.signal, AbortSignal.timeout(90000)])});
  if (!response.ok) throw Object.assign(new Error(`${method} ${path} returned HTTP ${response.status}`), {status: response.status});
  return response.status === 204 ? null : response.json();
}

async function until(action, predicate, message, attempts = 90) {
  return pollUntil(action, predicate, message, {attempts, pause, signal: abort.signal});
}

async function websocket() {
  activeSocket?.close();
  const socket = activeSocket = new WebSocket(base.replace("http", "ws") + "/api/websocket");
  const pending = new Map(); let sequence = 0;
  await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error("HA WebSocket authentication timed out")), 10000);
    socket.addEventListener("error", () => { clearTimeout(timer); reject(new Error("HA WebSocket connection failed")); }, {once: true});
    socket.addEventListener("message", event => {
      const value = JSON.parse(event.data);
      if (value.type === "auth_required") socket.send(JSON.stringify({type: "auth", access_token: tokens.access_token}));
      else if (value.type === "auth_ok") { clearTimeout(timer); resolve(); }
      else if (value.type === "auth_invalid") { clearTimeout(timer); reject(new Error("HA WebSocket authentication failed")); }
      else if (value.id && pending.has(value.id)) {
        const task = pending.get(value.id); pending.delete(value.id); clearTimeout(task.timer);
        value.success ? task.resolve(value.result) : task.reject(new Error(`HA WebSocket command failed: ${value.error?.code}`));
      }
    });
  });
  socket.addEventListener("close", () => { for (const task of pending.values()) { clearTimeout(task.timer); task.reject(new Error("HA WebSocket disconnected")); } pending.clear(); });
  return (type, data = {}) => new Promise((resolve, reject) => {
    const id = ++sequence;
    const timer = setTimeout(() => { pending.delete(id); reject(new Error(`HA WebSocket command timed out: ${type}`)); }, 10000);
    pending.set(id, {resolve, reject, timer}); socket.send(JSON.stringify({id, type, ...data}));
  });
}

async function optionsFlow(entry, step) {
  const flow = await request("/api/config/config_entries/options/flow", {handler: entry, show_advanced_options: false});
  return request(`/api/config/config_entries/options/flow/${flow.flow_id}`, {next_step_id: step});
}

const prayerColumns = {fajr_begin: "Fajr Begin", fajr_jamaat: "Fajr Jamaat", sunrise: "Sunrise", sehri_ends: "Sehri Ends", dhuhr_begin: "Dhuhr Begin", dhuhr_jamaat: "Dhuhr Jamaat", asr_begin: "Asr Begin", asr_jamaat: "Asr Jamaat", maghrib_begin: "Maghrib Begin", maghrib_jamaat: "Maghrib Jamaat", isha_begin: "Isha Begin", isha_jamaat: "Isha Jamaat", istewa: "Istewa"};
async function stage(entry, days, fajr = "06:00") {
  const csv = [["Date", ...Object.values(prayerColumns)].join(","), ...days.map(day => [day, fajr, "06:30", "07:30", "05:55", "12:00", "12:45", "15:00", "15:30", "17:30", "17:35", "19:00", "19:30", "12:00"].join(",")), ""].join("\n");
  let flow = await optionsFlow(entry, "import_csv");
  const form = new FormData(); form.append("file", new Blob([csv], {type: "text/csv"}), "synthetic-smoke.csv");
  const upload = await request("/api/file_upload", form, {form: true});
  flow = await request(`/api/config/config_entries/options/flow/${flow.flow_id}`, {file: upload.file_id, kind: "annual", year: Number(days[0].slice(0, 4))});
  assert.equal(flow.step_id, "map_columns");
  flow = await request(`/api/config/config_entries/options/flow/${flow.flow_id}`, {date_column: "Date", time_format: "24h", ...prayerColumns});
  assert.equal(flow.step_id, "review");
  assert.ok(flow.description_placeholders.summary.includes(days[0]));
  return flow;
}

async function addMosque(id, name) {
  let flow = await request("/api/config/config_entries/flow", {handler: "salah_timetable", show_advanced_options: false});
  assert.equal(flow.step_id, "user");
  flow = await request(`/api/config/config_entries/flow/${flow.flow_id}`, {name, mosque_id: id, time_zone: "UTC"});
  assert.equal(flow.type, "create_entry");
  const entry = flow.result.entry_id;
  await until(() => request("/api/config/config_entries/entry?domain=salah_timetable"), entries => entries.some(item => item.entry_id === entry && item.state === "loaded"), "Mosque did not load");
  return entry;
}

try {
  await mkdir(config, {mode: 0o700});
  await writeFile(join(config, "configuration.yaml"), "homeassistant:\n  name: Salah Smoke\n  time_zone: UTC\n  country: GB\n  latitude: 52.5\n  longitude: -1.5\n  elevation: 0\n  unit_system: metric\ndefault_config:\nlogger:\n  default: error\n", {mode: 0o600});
  try { await command("docker", ["image", "inspect", image]); }
  catch { console.log(`Pulling official HA ${options.version} image`); await command("docker", ["pull", image]); }
  const manifest = JSON.parse(await readFile(join(root, "custom_components/salah_timetable/manifest.json"), "utf8"));
  const expected = manifest.requirements.find(value => value.startsWith("pypdf==")).split("==")[1];
  const baseline = JSON.parse(await command("docker", ["run", "--rm", "--entrypoint", "python", image, "-I", "-c", dependencyProbe]));
  report.dependency_baseline = {version: baseline.version, module_version: baseline.module_version};
  if (options.requireFresh) {
    assert.equal(baseline.version, null, "Base image already contains pypdf metadata; cannot establish fresh installation");
    assert.equal(baseline.module_version, null, "Base image already imports pypdf; cannot establish fresh installation");
  }
  const trust = options.caBundle ? ["--mount", `type=bind,src=${options.caBundle},dst=/run/salah-ca-bundle.pem,readonly`, "--env", "SSL_CERT_FILE=/run/salah-ca-bundle.pem", "--env", "PIP_CERT=/run/salah-ca-bundle.pem"] : [];
  report.custom_ca_bundle = Boolean(options.caBundle);
  await command("docker", ["create", ...trust, "--name", container, "--publish", `127.0.0.1:${hostPort}:8123`, "--mount", `type=bind,src=${config},dst=/config`, "--mount", `type=bind,src=${join(root, "custom_components")},dst=/config/custom_components,readonly`, image]);
  created = true;
  if (options.preload) {
    const discovery = "import importlib.metadata,importlib.util,json,pathlib; d=importlib.metadata.distribution('pypdf'); print(json.dumps({'version':d.version,'package':str(pathlib.Path(importlib.util.find_spec('pypdf').origin).parent),'metadata':str(d.locate_file(next(p.parts[0] for p in d.files if p.parts[0].endswith('.dist-info'))))}))";
    const dependency = JSON.parse(await command(join(root, ".venv/bin/python"), ["-c", discovery]));
    assert.equal(dependency.version, expected, "Local pypdf must match the integration requirement");
    const site = baseline.site;
    assert.match(site, /^\/usr\/local\/lib\/python\d+\.\d+\/site-packages$/);
    await command("docker", ["cp", dependency.package, `${container}:${site}/pypdf`]);
    await command("docker", ["cp", dependency.metadata, `${container}:${site}/${basename(dependency.metadata)}`]);
    console.log(`Explicitly preloaded locked pypdf ${expected}; fresh dependency installation is not tested`);
  }
  await command("docker", ["start", container]);
  const port = await command("docker", ["port", container, "8123/tcp"]);
  assert.equal(port, `127.0.0.1:${hostPort}`); base = `http://${port}`;
  console.log(`Waiting for disposable HA ${options.version}`);
  await until(() => request("/api/onboarding", undefined, {auth: false}), value => Array.isArray(value), "HA did not start", 120);
  const client = base + "/";
  userRequested = true;
  const user = await request("/api/onboarding/users", {name: "Salah Smoke", username: "salah_smoke", password: randomBytes(24).toString("hex"), client_id: client, language: "en"}, {auth: false});
  tokens = await request("/auth/token", new URLSearchParams({grant_type: "authorization_code", code: user.auth_code, client_id: client}), {auth: false, form: true});
  for (const [step, body] of [["core_config", {}], ["analytics", {}], ["integration", {client_id: client, redirect_uri: `${client}?auth_callback=1`}]]) {
    const remaining = await request("/api/onboarding", undefined, {auth: false});
    if (remaining.some(item => item.step === step && !item.done)) await request(`/api/onboarding/${step}`, body);
  }
  await waitForRunning(request, until);
  report.checks.push("onboarding", "ha_running_before_configuration");
  const entry = await addMosque("smoke", "Smoke Mosque");
  const installed = JSON.parse(await command("docker", ["exec", container, "python", "-I", "-c", dependencyProbe]));
  report.dependency = dependencyEvidence(baseline, installed, expected, {preloaded: options.preload, requireFresh: options.requireFresh});
  if (report.dependency.fresh_install_verified) report.checks.push("fresh_manifest_dependency_installation");
  const today = new Date().toISOString().slice(0, 10);
  // Keep annual sources within their explicit year, including a December 31 run.
  const next = new Date(Date.parse(`${today}T12:00:00Z`) + 86400000).toISOString().slice(0, 10);
  const days = next.slice(0, 4) === today.slice(0, 4) ? [today, next] : [today];
  let flow = await stage(entry, days);
  await request(`/api/config/config_entries/options/flow/${flow.flow_id}`, {decision: "approve"});
  const state = async key => (await request("/api/states")).find(item => item.entity_id === `sensor.smoke_mosque_${key}`);
  await until(() => state("fajr_beginning"), value => value?.state === `${today}T06:00:00+00:00`, "Approved Fajr missing");
  let states = await request("/api/states");
  const ids = states.filter(item => item.entity_id.startsWith("sensor.smoke_mosque_")).map(item => item.entity_id).sort();
  assert.equal(ids.length, 26); report.checks.push("mosque_config_flow", "authenticated_csv_upload_mapping_review_approval", "26_sensors");
  const calendarId = "calendar.smoke_mosque_prayer_calendar";
  const calendarPath = `/api/calendars/${calendarId}?start=${today}T00:00:00Z&end=${new Date(Date.parse(`${today}T00:00:00Z`) + 86400000).toISOString()}`;
  const calendarEvents = () => request(calendarPath);
  const approvedEvents = await calendarEvents();
  const calendarFajr = approvedEvents.find(event => event.summary === "Fajr beginning");
  assert.equal(calendarFajr?.start.dateTime, `${today}T06:00:00+00:00`);
  assert.equal(Date.parse(calendarFajr.end.dateTime) - Date.parse(calendarFajr.start.dateTime), 60000);
  assert.ok(calendarFajr.uid);
  assert.equal((await request("/api/calendars")).filter(item => item.entity_id === calendarId).length, 1);
  report.checks.push("native_calendar_approved_instant_events");
  let profileFlow = await optionsFlow(entry, "publication_profile");
  assert.equal(profileFlow.step_id, "publication_profile");
  profileFlow = await request(`/api/config/config_entries/options/flow/${profileFlow.flow_id}`, {profile_id: "nms_annual_2026_v1", year: 2026});
  assert.equal(profileFlow.errors.base, "invalid_publication_profile");
  assert.ok(profileFlow.description_placeholders.detail.includes("Europe/London"));
  await request(`/api/config/config_entries/options/flow/${profileFlow.flow_id}`, undefined, {method: "DELETE"});
  report.checks.push("publication_profile_picker_timezone_guard");
  let ws = await websocket();
  const version = JSON.parse(await readFile(join(root, "custom_components/salah_timetable/manifest.json"), "utf8")).version;
  const cardUrl = `/salah_timetable/salah-timetable-card.js?v=${version}`;
  assert.equal((await ws("lovelace/resources")).filter(item => item.url === cardUrl).length, 1);
  await ws("lovelace/dashboards/create", {url_path: "salah-smoke", title: "Salah Smoke", show_in_sidebar: true, require_admin: false, mode: "storage"});
  await ws("lovelace/config/save", {url_path: "salah-smoke", config: {views: [{title: "Salah Smoke", path: "smoke", cards: [{type: "custom:salah-timetable-card", entity: "sensor.smoke_mosque_prayer_timetable"}]}]}});
  report.checks.push("automatic_resource_registration", "dashboard_configuration");
  flow = await optionsFlow(entry, "ramadan");
  await request(`/api/config/config_entries/options/flow/${flow.flow_id}`, {ramadan_mode: "auto", ramadan_start: today, ramadan_end: today, ramadan_adjustment: 0, ramadan_source_id: "__auto__"});
  await until(() => state("ramadan_status"), value => value?.state === "active", "Ramadan activation failed");
  assert.equal((await state("iftar")).state, `${today}T17:30:00+00:00`);
  assert.equal((await state("taraweeh")).state, "unavailable");
  assert.equal((await state("taraweeh_status")).state, "after_isha_jamaat");
  report.checks.push("confirmed_ramadan", "iftar_fallback", "taraweeh_text_without_timestamp");
  const second = await addMosque("second", "Second Mosque");
  await until(() => request("/api/states"), value => value.filter(item => item.entity_id.startsWith("sensor.second_mosque_")).length === ids.length, "Second mosque sensors missing");
  let secondFlow = await stage(second, days, "06:22");
  await request(`/api/config/config_entries/options/flow/${secondFlow.flow_id}`, {decision: "approve"});
  await until(() => request("/api/states"), value => value.find(item => item.entity_id === "sensor.second_mosque_fajr_beginning")?.state === `${today}T06:22:00+00:00`, "Independent second mosque approval missing");
  assert.equal((await state("fajr_beginning")).state, `${today}T06:00:00+00:00`);
  const secondIds = (await request("/api/states")).filter(item => item.entity_id.startsWith("sensor.second_mosque_")).map(item => item.entity_id).sort();
  assert.equal(secondIds.length, ids.length);
  await request(`/api/config/config_entries/entry/${second}`, undefined, {method: "DELETE"});
  await until(() => request("/api/states"), value => !value.some(item => item.entity_id.startsWith("sensor.second_mosque_")), "Deleted mosque retained live sensors");
  assert.deepEqual((await request("/api/states")).filter(item => item.entity_id.startsWith("sensor.smoke_mosque_")).map(item => item.entity_id).sort(), ids);
  assert.equal((await state("fajr_beginning")).state, `${today}T06:00:00+00:00`);
  const readded = await addMosque("second", "Second Mosque");
  await until(() => request("/api/states"), value => value.filter(item => item.entity_id.startsWith("sensor.second_mosque_")).length === ids.length, "Re-added mosque sensors missing");
  assert.equal((await request("/api/states")).find(item => item.entity_id === "sensor.second_mosque_fajr_beginning")?.state, "unavailable", "Removing a config entry must delete that mosque's storage");
  assert.deepEqual((await request("/api/states")).filter(item => item.entity_id.startsWith("sensor.smoke_mosque_")).map(item => item.entity_id).sort(), ids);
  assert.equal((await ws("lovelace/resources")).filter(item => item.url === cardUrl).length, 1);
  await request(`/api/config/config_entries/entry/${readded}`, undefined, {method: "DELETE"});
  report.checks.push("two_mosques_independent_approval", "entry_remove_readd_clears_only_own_storage", "no_stale_readded_entities", "resource_deduplication_after_readd");
  flow = await stage(entry, days, "06:11");
  if (options.verifyBackupRestore) {
    // HA registries are persisted asynchronously; require the full source
    // snapshot on disk before creating and comparing a real backup archive.
    await until(
      () => command("docker", ["exec", container, "python", "-c",
        "from pathlib import Path; p=Path('/config/.storage'); "
        + "required=['core.config_entries','core.entity_registry','core.device_registry',"
        + JSON.stringify(`salah_timetable.${entry}`) + "]; "
        + "print('ready' if all((p/n).is_file() for n in required) else 'pending')"]),
      value => value === "ready",
      "Home Assistant registries and timetable were not persisted before backup",
      120,
    );
    // backup.create is Home Assistant's real Container backup action. Exercise
    // official extraction in a *different* throwaway configuration volume.
    await request("/api/services/backup/create", {});
    const archiveName = await until(
      async () => command("docker", ["exec", container, "python", "-c",
        "from pathlib import Path; import tarfile; p=next(iter(sorted(Path('/config/backups').glob('*.tar'))), None); print(p.name if p and tarfile.is_tarfile(p) else '')"]),
      name => name.endsWith(".tar"),
      "Official Home Assistant backup archive was not finalized",
      120,
    );
    assert.match(archiveName, /^[^/]+\.tar$/, "Unsafe backup archive filename");
    const archive = join(working, "synthetic-ha-backup.tar");
    await command("docker", ["cp", `${container}:/config/backups/${archiveName}`, archive]);
    const output = await command("python3", [
      "-m", "scripts.disposable_backup_restore",
      "--backup", archive, "--original", config,
      "--ha-version", options.version, "--confirm-disposable",
    ]);
    assert.match(output, /Verified restored config safely:/);
    report.checks.push("official_backup_archive_restored_into_second_disposable_config");
  }
  await request(`/api/config/config_entries/options/flow/${flow.flow_id}`, undefined, {method: "DELETE"});
  assert.equal((await calendarEvents()).find(event => event.summary === "Fajr beginning").uid, calendarFajr.uid);
  assert.equal((await calendarEvents()).find(event => event.summary === "Fajr beginning").start.dateTime, `${today}T06:00:00+00:00`);
  report.checks.push("calendar_excludes_pending_proposal");
  activeSocket.close(); activeSocket = undefined;
  await waitForRunning(request, until);
  await command("docker", ["restart", container]);
  assert.equal(await command("docker", ["port", container, "8123/tcp"]), `127.0.0.1:${hostPort}`);
  await waitForRunning(request, until);
  await waitForEntry(request, until, entry);
  await until(async () => {
    const value = await state("fajr_beginning");
    report.restart_fajr = {present: Boolean(value), available: Boolean(value && !["unavailable", "unknown"].includes(value.state)), matches_approved: value?.state === `${today}T06:00:00+00:00`};
    return report.restart_fajr;
  }, value => value.matches_approved, "Approved Fajr mismatch after HA RUNNING and mosque loaded", 120);
  assert.equal((await state("ramadan_status")).state, "active");
  flow = await optionsFlow(entry, "review"); assert.equal(flow.step_id, "review");
  await request(`/api/config/config_entries/options/flow/${flow.flow_id}`, {decision: "reject"});
  assert.equal((await state("fajr_beginning")).state, `${today}T06:00:00+00:00`);
  assert.equal((await calendarEvents()).find(event => event.summary === "Fajr beginning").uid, calendarFajr.uid);
  report.checks.push("calendar_ids_survive_restart_and_rejection");
  ws = await websocket();
  assert.equal((await ws("lovelace/resources")).filter(item => item.url === cardUrl).length, 1);
  assert.deepEqual((await request("/api/states")).filter(item => item.entity_id.startsWith("sensor.smoke_mosque_")).map(item => item.entity_id).sort(), ids);
  report.checks.push("restart_approved_pending_ramadan_and_ids", "rejection_preserves_approved", "resource_deduplication");
  // Onboarding may create optional network integrations; disable them only in this
  // disposable instance so unrelated network errors do not obscure the UI check.
  for (const item of await request("/api/config/config_entries/entry")) if (["radio_browser", "met"].includes(item.domain)) await request(`/api/config/config_entries/entry/${item.entry_id}`, undefined, {method: "DELETE"});
  const runtime = await request("/api/config"); assert.equal(runtime.version, options.version);
  await request(`/api/config/config_entries/entry/${entry}/reload`, {});
  await until(() => state("prayer_timetable"), value => value?.state === today, "Dashboard data missing after reload");
  report.integration_version = version;
  report.source_commit = await command("git", ["-C", root, "rev-parse", "HEAD"]);
  report.working_tree_dirty = Boolean(await command("git", ["-C", root, "status", "--porcelain"]));
  report.image_id = await command("docker", ["image", "inspect", "--format", "{{.Id}}", image]);
  report.browser = await runBrowserSmoke({base, tokens: {...tokens, clientId: client, hassUrl: base, expires: Date.now() + tokens.expires_in * 1000}, output: options.output, signal: abort.signal});
  report.checks.push("real_frontend_card_picker_editor", "light_dark_theme", "keyboard_title_and_focus", "phone_tablet_viewports", "text_scale");
  report.status = "passed";
  console.log(`Live HA ${options.version} passed ${report.checks.length} acceptance checks`);
  if (options.output) { await mkdir(options.output, {recursive: true}); await writeFile(join(options.output, "results.json"), JSON.stringify(report, null, 2) + "\n"); }
} catch (error) {
  report.status = "failed";
  report.failure = error.message;
  console.error(`Live smoke failed: ${error.message}`);
  // Startup logs are safe before credentials exist; never export configuration
  // files or authenticated-session logs into the public result directory.
  if (created && !userRequested) {
    console.error(await command("docker", ["logs", "--tail", "40", container], {cleanup: true}).catch(() => "Startup logs unavailable"));
  }
  if (options.output) { await mkdir(options.output, {recursive: true}); await writeFile(join(options.output, "results.json"), JSON.stringify(report, null, 2) + "\n"); }
  throw error;
} finally {
  clearTimeout(limit); activeSocket?.close();
  if (created) await command("docker", ["rm", "--force", container], {cleanup: true}).catch(() => {});
  // HA writes root-owned private files. A fresh, short-lived container removes
  // only the script-created bind directory after the tested container is gone.
  await command("docker", ["run", "--rm", "--pull=never", "--entrypoint", "python", "--mount", `type=bind,src=${config},dst=/cleanup`, image, "-c", "from pathlib import Path; import shutil; [(shutil.rmtree(p) if p.is_dir() and not p.is_symlink() else p.unlink()) for p in Path('/cleanup').iterdir()]"], {cleanup: true}).catch(() => {});
  await rm(working, {recursive: true, force: true});
}
