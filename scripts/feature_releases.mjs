// Run only from trusted main. PR files are read as data, never executed.
import { pathToFileURL } from 'node:url';

export const MARKER = '<!-- salah-feature-release:v1 -->';
const TAG = /^v\d+\.\d+\.\d+-pr\.([1-9]\d*)\.([a-f0-9]{40})$/;
const WORKFLOWS = ['validate.yml', 'codeql.yml'];

export function eligible(pr, repository) {
  return pr.state === 'open' && !pr.draft && pr.base.ref === 'main'
    && pr.head.repo?.full_name === repository && pr.head.ref !== 'main'
    && pr.mergeable !== false;
}

export function latestPassed(runs, pr) {
  const matching = runs.filter(run => run.event === 'pull_request'
    && run.head_sha === pr.head.sha && run.head_branch === pr.head.ref
    && run.pull_requests?.some(item => item.number === pr.number));
  matching.sort((a, b) => b.id - a.id || b.run_attempt - a.run_attempt);
  return matching[0]?.status === 'completed' && matching[0]?.conclusion === 'success';
}

export function githubClient(repository, token) {
  if (!/^[\w.-]+\/[\w.-]+$/.test(repository) || !token) {
    throw new Error('GITHUB_REPOSITORY and GH_TOKEN are required');
  }
  async function request(method, path, body) {
    const response = await fetch(`https://api.github.com/repos/${repository}/${path}`, {
      method,
      headers: {
        Authorization: `Bearer ${token}`, Accept: 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28', 'Content-Type': 'application/json',
      },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: AbortSignal.timeout(30_000),
    });
    if (!response.ok) {
      const error = new Error(`GitHub ${method} ${path}: HTTP ${response.status}`);
      error.status = response.status;
      throw error;
    }
    return response.status === 204 ? null : response.json();
  }
  async function list(path, key) {
    const result = [];
    for (let page = 1; ; page++) {
      const data = await request('GET', `${path}${path.includes('?') ? '&' : '?'}per_page=100&page=${page}`);
      const items = key ? data[key] : data;
      result.push(...items);
      if (items.length < 100) return result;
    }
  }
  return { request, list };
}

async function remove(api, path) {
  try { await api.request('DELETE', path); }
  catch (error) { if (error.status !== 404) throw error; }
}

async function passed(api, pr) {
  for (const workflow of WORKFLOWS) {
    const runs = await api.list(`actions/workflows/${workflow}/runs?event=pull_request&head_sha=${pr.head.sha}`, 'workflow_runs');
    if (!latestPassed(runs, pr)) return false;
  }
  const status = await api.request('GET', `commits/${pr.head.sha}/status`);
  return !status.total_count || status.state === 'success';
}

export async function reconcile(api, repository, log = console.log) {
  const releases = await api.list('releases');
  // Include orphan tags left by an interrupted create/delete operation.
  const refs = await api.list('git/matching-refs/tags/v');
  const managed = releases.filter(release => TAG.test(release.tag_name)
    && release.prerelease && release.body?.startsWith(MARKER));
  const numbers = new Set((await api.list('pulls?state=open&base=main')).map(pr => pr.number));
  for (const ref of refs) {
    const match = TAG.exec(ref.ref.replace('refs/tags/', ''));
    if (match) numbers.add(Number(match[1]));
  }
  for (const release of managed) numbers.add(Number(TAG.exec(release.tag_name)[1]));

  const failures = [];
  for (const number of numbers) {
    try {
      const pr = await api.request('GET', `pulls/${number}`);
      const ownReleases = managed.filter(release => Number(TAG.exec(release.tag_name)[1]) === number);
      const ownTags = refs.map(ref => ref.ref.replace('refs/tags/', ''))
        .filter(tag => Number(TAG.exec(tag)?.[1]) === number);
      const ready = eligible(pr, repository);
      // Revoke stale candidates immediately; failing new CI must not advertise old code.
      const stale = new Set([...ownTags, ...ownReleases.map(release => release.tag_name)]
        .filter(tag => !ready || TAG.exec(tag)[2] !== pr.head.sha));
      async function deleteTag(tag) {
        const release = releases.find(item => item.tag_name === tag);
        if (release && !managed.includes(release)) throw new Error(`Refusing to alter unmanaged release ${tag}`);
        if (release) await remove(api, `releases/${release.id}`);
        await remove(api, `git/refs/tags/${tag}`);
        log(`Removed ${tag}`);
      }
      for (const tag of stale) await deleteTag(tag);
      if (!ready) continue;
      if (!await passed(api, pr)) {
        for (const tag of new Set([...ownTags, ...ownReleases.map(item => item.tag_name)])) {
          if (!stale.has(tag)) await deleteTag(tag);
        }
        log(`PR #${number}: waiting for current Validate and CodeQL`);
        continue;
      }
      const manifestFile = await api.request('GET', `contents/custom_components/salah_timetable/manifest.json?ref=${pr.head.sha}`);
      const manifest = JSON.parse(Buffer.from(manifestFile.content, 'base64').toString('utf8'));
      if (!/^\d+\.\d+\.\d+$/.test(manifest.version)) throw new Error('Expected a stable numeric manifest version');
      const tag = `v${manifest.version}-pr.${number}.${pr.head.sha}`;
      // Re-read just before mutation, and again afterwards, to handle pushes/merges during API calls.
      const fresh = await api.request('GET', `pulls/${number}`);
      if (!eligible(fresh, repository) || fresh.head.sha !== pr.head.sha) continue;
      const existing = refs.find(ref => ref.ref === `refs/tags/${tag}`);
      if (existing && (existing.object.type !== 'commit' || existing.object.sha !== pr.head.sha)) {
        throw new Error(`Candidate tag points to unexpected source: ${tag}`);
      }
      if (ownReleases.some(item => item.tag_name === tag) && existing) continue;
      if (!existing) await api.request('POST', 'git/refs', { ref: `refs/tags/${tag}`, sha: pr.head.sha });
      const collision = releases.find(item => item.tag_name === tag);
      if (collision && !managed.includes(collision)) throw new Error(`Unmanaged release collision: ${tag}`);
      if (!collision) {
        const release = await api.request('POST', 'releases', {
          tag_name: tag, target_commitish: pr.head.sha,
          name: `PR #${number}: ${pr.title}`, prerelease: true, draft: false, make_latest: 'false',
          body: `${MARKER}\n\nTemporary Home Assistant test release for ${pr.html_url}.\n\n`
            + `Branch: ${pr.head.ref}\nCommit: ${pr.head.sha}\n\n`
            + 'Validate and CodeQL passed for this PR head. Install this version through HACS '
            + 'with pre-releases enabled, then restart Home Assistant and refresh the browser cache. '
            + 'The source archive contains custom_components/salah_timetable for manual installation.\n\n'
            + 'Automatically replaced after further commits pass CI and removed when the PR is closed or merged. '
            + 'The integration manifest version is unchanged. Return to a stable release after testing.\n',
        });
        releases.push(release);
        managed.push(release);
      }
      const after = await api.request('GET', `pulls/${number}`);
      if (!eligible(after, repository) || after.head.sha !== pr.head.sha) await deleteTag(tag);
      else log(`PR #${number}: ${tag}`);
    } catch (error) {
      failures.push(`PR #${number}: ${error.message}`);
    }
  }
  if (failures.length) throw new Error(failures.join('\n'));
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  await reconcile(githubClient(process.env.GITHUB_REPOSITORY, process.env.GH_TOKEN), process.env.GITHUB_REPOSITORY);
}
