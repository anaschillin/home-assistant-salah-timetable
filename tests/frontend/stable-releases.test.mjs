import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import {
  assessRelease, compareStableVersions, latestMainPushPassed, planFromGitHub,
} from '../../scripts/stable_releases.mjs';

const sha = 'a'.repeat(40);
const oldSha = 'b'.repeat(40);
const run = (overrides = {}) => ({
  id: 42, run_attempt: 1, event: 'push', head_branch: 'main', head_sha: sha,
  status: 'completed', conclusion: 'success', ...overrides,
});
const passing = [run()];
const candidate = (overrides = {}) => ({
  candidateSha: sha, mainSha: sha, version: '1.2.3',
  validateRuns: passing, codeqlRuns: passing,
  tagSha: null, release: null, releases: [],
  ...overrides,
});

test('stable version comparison is numeric and disallows prerelease names', () => {
  assert.equal(compareStableVersions('1.10.0', '1.9.9'), 1);
  assert.equal(compareStableVersions('2.0.0', '2.0.0'), 0);
  assert.equal(compareStableVersions('0.8.9', '1.0.0'), -1);
  assert.throws(() => compareStableVersions('1.2.3-rc1', '1.2.3'), /numeric/);
});

test('only the latest completed successful push for exact main SHA qualifies', () => {
  assert.equal(latestMainPushPassed(passing, sha), true);
  for (const invalid of [
    { event: 'pull_request' }, { head_branch: 'other' },
    { head_sha: oldSha }, { status: 'in_progress' },
    { conclusion: 'failure' }, { conclusion: 'cancelled' },
  ]) assert.equal(latestMainPushPassed([run(invalid)], sha), false);
  assert.equal(latestMainPushPassed([run(), run({ id: 43, conclusion: 'failure' })], sha), false);
  assert.equal(latestMainPushPassed([run({ id: 43, conclusion: 'failure' }), run()], sha), false);
  assert.equal(latestMainPushPassed([run({ id: 43, run_attempt: 1 }), run({ id: 43, run_attempt: 2, conclusion: 'failure' })], sha), false);
});

test('publish only once both security and validation workflows passed', () => {
  assert.deepEqual(assessRelease(candidate()), { publish: true, tag: 'v1.2.3', sha });
  assert.match(assessRelease(candidate({ codeqlRuns: [] })).reason, /awaiting successful/);
  assert.match(assessRelease(candidate({ validateRuns: [run({ conclusion: 'failure' })] })).reason, /awaiting successful/);
  assert.match(assessRelease(candidate({ mainSha: oldSha })).reason, /main moved/);
});

test('existing published releases are idempotent; draft/prerelease is protected', () => {
  const stable = { tag_name: 'v1.2.3', draft: false, prerelease: false };
  assert.match(assessRelease(candidate({ release: stable })).reason, /already exists/);
  for (const state of [{ draft: true, prerelease: false }, { draft: false, prerelease: true }]) {
    assert.throws(() => assessRelease(candidate({ release: state })), /review it manually/);
  }
});

test('cannot retag other source commits or regress below a published stable release', () => {
  assert.throws(() => assessRelease(candidate({ tagSha: oldSha })), /different commit/);
  assert.equal(assessRelease(candidate({ tagSha: sha })).publish, true);
  assert.throws(() => assessRelease(candidate({
    releases: [{ tag_name: 'v1.3.0', draft: false, prerelease: false }],
  })), /newer stable release/);
  assert.equal(assessRelease(candidate({
    releases: [{ tag_name: 'v2.0.0-pr.12.' + sha, draft: false, prerelease: true }],
  })).publish, true);
  assert.throws(() => assessRelease(candidate({ version: '1.2.3-rc1' })), /non-stable/);
});

test('API gate resolves annotated tags and checks both exact workflow runs', async () => {
  const api = {
    async request(method, path) {
      assert.equal(method, 'GET');
      if (path === 'git/ref/heads/main') return { object: { sha } };
      if (path === 'releases/tags/v1.2.3') throw Object.assign(new Error('Missing'), { status: 404 });
      if (path === 'git/ref/tags/v1.2.3') return { object: { type: 'tag', sha: oldSha } };
      if (path === 'git/tags/' + oldSha) return { object: { type: 'commit', sha } };
      throw Error('Unexpected ' + path);
    },
    async list(path) {
      if (path === 'releases') return [];
      if (path.includes('/runs?')) return passing;
      throw Error('Unexpected list ' + path);
    },
  };
  assert.equal((await planFromGitHub(api, sha, '1.2.3')).publish, true);
});

test('API errors are not mistaken for missing releases', async () => {
  const api = {
    async request(method, path) {
      if (path === 'git/ref/heads/main') return { object: { sha } };
      throw Object.assign(new Error('Forbidden'), { status: 403 });
    },
    async list() { return passing; },
  };
  await assert.rejects(planFromGitHub(api, sha, '1.2.3'), /Forbidden/);
});

test('publication workflow has isolated write permissions and trusted-main gates', () => {
  const source = readFileSync('.github/workflows/stable-release.yml', 'utf8');
  assert.match(source, /workflows: \[Validate, CodeQL\]/);
  assert.match(source, /types: \[completed\]/);
  assert.match(source, /github\.event\.workflow_run\.event == 'push'/);
  assert.match(source, /github\.event\.workflow_run\.head_branch == 'main'/);
  assert.match(source, /github\.event\.workflow_run\.head_repository\.full_name == github\.repository/);
  assert.match(source, /ref: main/);
  assert.match(source, /persist-credentials: false/);
  assert.match(source, /python scripts\/check_asset_provenance\.py --require-cleared/);
  assert.match(source, /node scripts\/stable_releases\.mjs --assert/);
  assert.match(source, /gh release create "\$RELEASE_TAG" --verify-tag/);
  assert.doesNotMatch(source, /pull_request_target:/);
});
