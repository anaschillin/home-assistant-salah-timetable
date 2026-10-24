/** Verify that HA installed the manifest pin rather than inheriting/preloading it. */
import assert from "node:assert/strict";

export const dependencyProbe = `import importlib.metadata as metadata, importlib.util, json, sysconfig
try:
    version = metadata.version('pypdf')
except metadata.PackageNotFoundError:
    version = None
spec = importlib.util.find_spec('pypdf')
if spec is not None:
    import pypdf
    module_version = pypdf.__version__
else:
    module_version = None
print(json.dumps({'version': version, 'module_version': module_version, 'site': sysconfig.get_path('purelib')}))`;

export function dependencyEvidence(before, after, expected, {preloaded = false, requireFresh = false} = {}) {
  assert.equal(after.version, expected, "Installed pypdf metadata does not match the manifest pin");
  assert.equal(after.module_version, expected, "Imported pypdf does not match the manifest pin");
  const fresh = !preloaded && before.version === null && before.module_version === null;
  if (requireFresh) assert.ok(fresh, "Fresh dependency acceptance requires pypdf to be absent from the base image and not preloaded");
  return {expected_version: expected, before_version: before.version, before_module_version: before.module_version, installed_version: after.version, installed_module_version: after.module_version, fresh_install_verified: fresh};
}
