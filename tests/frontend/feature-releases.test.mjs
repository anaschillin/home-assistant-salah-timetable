import assert from 'node:assert/strict';
import test from 'node:test';
import { eligible, latestPassed, MARKER, reconcile } from '../../scripts/feature_releases.mjs';

const repository = 'owner/repo';
const sha = 'a'.repeat(40);
const oldSha = 'b'.repeat(40);
const tagFor = value => `v1.2.3-pr.12.${value}`;
const makePR = () => ({
  number: 12, state: 'open', draft: false, base: { ref: 'main' },
  head: { sha, ref: 'feat/example', repo: { full_name: repository } },
  title: 'Example feature', html_url: 'https://github.com/owner/repo/pull/12',
});
const makeRun = (overrides = {}) => ({
  id: 100, run_attempt: 1, status: 'completed', conclusion: 'success',
  event: 'pull_request', head_sha: sha, head_branch: 'feat/example',
  pull_requests: [{ number: 12 }], ...overrides,
});

function fixture({ old, orphan, pr = makePR(), runs = [makeRun()], status, afterCreate } = {}) {
  const releases = old ? [{ id: 1, tag_name: tagFor(old), prerelease: true, body: MARKER }] : [];
  const refs = old || orphan ? [{ ref: `refs/tags/${tagFor(old || orphan)}`, object: { type: 'commit', sha: old || orphan } }] : [];
  const writes = [];
  const api = {
    async list(path) {
      if (path === 'releases') return [...releases];
      if (path === 'git/matching-refs/tags/v') return structuredClone(refs);
      if (path.startsWith('pulls?')) return pr.state === 'open' ? [pr] : [];
      if (path.startsWith('actions/workflows/')) return runs;
      throw new Error(`Unexpected list ${path}`);
    },
    async request(method, path, body) {
      if (method === 'GET') {
        if (path === 'pulls/12') return structuredClone(pr);
        if (path.endsWith('/status')) return status || { total_count: 0 };
        if (path.startsWith('contents/')) return { content: Buffer.from('{"version":"1.2.3"}').toString('base64') };
      }
      writes.push({ method, path, body });
      if (method === 'DELETE') {
        if (path.startsWith('releases/')) releases.splice(releases.findIndex(item => path === `releases/${item.id}`), 1);
        else refs.splice(refs.findIndex(item => path === `git/${item.ref}`), 1);
        return null;
      }
      if (path === 'git/refs') refs.push({ ref: body.ref, object: { type: 'commit', sha: body.sha } });
      if (path === 'releases') {
        const release = { id: 2, ...body };
        releases.push(release);
        afterCreate?.(pr);
        return release;
      }
      return {};
    },
  };
  return { api, writes, releases, refs, pr };
}

test('only ready same-repository PRs targeting main qualify', () => {
  assert.equal(eligible(makePR(), repository), true);
  for (const changes of [{ draft: true }, { state: 'closed' }, { mergeable: false }, { base: { ref: 'other' } }, { head: { repo: null } }]) {
    assert.equal(eligible({ ...makePR(), ...changes }, repository), false);
  }
});

test('latest CI result wins; missing, stale, foreign and unfinished evidence fails closed', () => {
  assert.equal(latestPassed([makeRun()], makePR()), true);
  for (const changes of [{ status: 'in_progress' }, { conclusion: 'failure' }, { head_sha: oldSha }, { event: 'push' }, { pull_requests: [] }, { head_branch: 'other' }]) {
    assert.equal(latestPassed([makeRun(changes)], makePR()), false);
  }
  assert.equal(latestPassed([makeRun(), makeRun({ id: 101, conclusion: 'cancelled' })], makePR()), false);
  assert.equal(latestPassed([], makePR()), false);
});

test('publish a prerelease at the exact branch head; repeated notifications are idempotent', async () => {
  const f = fixture();
  await reconcile(f.api, repository, () => {});
  assert.equal(f.releases.length, 1);
  assert.equal(f.refs[0].object.sha, sha);
  assert.equal(f.releases[0].make_latest, 'false');
  assert.equal(f.releases[0].prerelease, true);
  assert.equal(f.releases[0].target_commitish, sha);
  const count = f.writes.length;
  await reconcile(f.api, repository, () => {});
  assert.equal(f.writes.length, count);
});

test('new commits revoke the previous release and tag before pending CI completes', async () => {
  const f = fixture({ old: oldSha, runs: [makeRun({ status: 'in_progress' })] });
  await reconcile(f.api, repository, () => {});
  assert.equal(f.releases.length, 0);
  assert.equal(f.refs.length, 0);
  assert.deepEqual(f.writes.map(item => item.method), ['DELETE', 'DELETE']);
});

test('a passing new head replaces the old release with exactly one candidate', async () => {
  const f = fixture({ old: oldSha });
  await reconcile(f.api, repository, () => {});
  assert.deepEqual(f.releases.map(item => item.tag_name), [tagFor(sha)]);
  assert.equal(f.refs.length, 1);
});

test('merged, closed, draft and retargeted PRs remove releases and orphan tags', async () => {
  for (const changes of [{ state: 'closed', merged: true }, { state: 'closed' }, { draft: true }, { base: { ref: 'other' } }]) {
    const f = fixture({ old: sha, pr: { ...makePR(), ...changes } });
    await reconcile(f.api, repository, () => {});
    assert.equal(f.releases.length, 0);
    assert.equal(f.refs.length, 0);
  }
  const f = fixture({ orphan: sha, pr: { ...makePR(), state: 'closed' } });
  await reconcile(f.api, repository, () => {});
  assert.equal(f.refs.length, 0);
});

test('interrupted creation resumes from an existing valid tag', async () => {
  const f = fixture({ orphan: sha });
  await reconcile(f.api, repository, () => {});
  assert.equal(f.releases.length, 1);
  assert.equal(f.writes.filter(item => item.path === 'git/refs').length, 0);
});

test('external failing status blocks publication', async () => {
  const f = fixture({ status: { total_count: 1, state: 'failure' } });
  await reconcile(f.api, repository, () => {});
  assert.equal(f.writes.length, 0);
});

test('a push or merge during publication removes the raced candidate', async () => {
  for (const update of [pr => { pr.state = 'closed'; }, pr => { pr.head.sha = oldSha; }]) {
    const f = fixture({ afterCreate: update });
    await reconcile(f.api, repository, () => {});
    assert.equal(f.releases.length, 0);
    assert.equal(f.refs.length, 0);
  }
});

test('stable and unmanaged releases are protected', async () => {
  const f = fixture({ old: oldSha });
  f.releases[0].body = 'Manually maintained';
  await assert.rejects(reconcile(f.api, repository, () => {}), /unmanaged release/);
  assert.equal(f.writes.length, 0);
  const stable = fixture();
  stable.releases.push({ id: 3, tag_name: 'v1.2.3', prerelease: false });
  await reconcile(stable.api, repository, () => {});
  assert.equal(stable.releases.some(item => item.tag_name === 'v1.2.3'), true);
});

test('unexpected tag targets are never silently reused', async () => {
  const f = fixture({ old: sha });
  f.refs[0].object.sha = oldSha;
  await assert.rejects(reconcile(f.api, repository, () => {}), /unexpected source/);
  assert.equal(f.writes.length, 0);
});

test('API permission failures do not get mistaken for missing resources', async () => {
  const f = fixture({ old: oldSha });
  const request = f.api.request;
  f.api.request = async (method, ...args) => {
    if (method === 'DELETE') throw Object.assign(new Error('Forbidden'), { status: 403 });
    return request(method, ...args);
  };
  await assert.rejects(reconcile(f.api, repository, () => {}), /Forbidden/);
  assert.equal(f.releases.length, 1);
});
