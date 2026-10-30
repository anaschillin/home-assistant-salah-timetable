// Release planning is read-only: publication happens only after both main CI lanes pass.
// This script runs from trusted main in a workflow_run with a write-scoped token.
import { appendFileSync, readFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { pathToFileURL } from 'node:url';
import { githubClient } from './feature_releases.mjs';

export const STABLE_VERSION = /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/;

export function compareStableVersions(left, right) {
  if (!STABLE_VERSION.test(left) || !STABLE_VERSION.test(right)) {
    throw new Error('Stable release versions must be numeric MAJOR.MINOR.PATCH');
  }
  const a = left.split('.').map(BigInt);
  const b = right.split('.').map(BigInt);
  for (let i = 0; i < 3; i++) {
    if (a[i] !== b[i]) return a[i] > b[i] ? 1 : -1;
  }
  return 0;
}

export function latestMainPushPassed(runs, sha) {
  const relevant = runs.filter(run =>
    run.event === 'push' && run.head_branch === 'main' && run.head_sha === sha);
  relevant.sort((a, b) => b.id - a.id || b.run_attempt - a.run_attempt);
  return relevant[0]?.status === 'completed' && relevant[0]?.conclusion === 'success';
}

export function assessRelease({ candidateSha, mainSha, version, validateRuns, codeqlRuns,
  tagSha, release, releases }) {
  if (!STABLE_VERSION.test(version)) {
    throw new Error('Refusing to publish a non-stable integration version');
  }
  const tag = 'v' + version;
  if (!/^[0-9a-f]{40}$/.test(candidateSha) || !/^[0-9a-f]{40}$/.test(mainSha)) {
    throw new Error('Expected verified commit SHA values');
  }
  if (candidateSha !== mainSha) return { publish: false, tag, reason: 'main moved' };
  if (tagSha !== null && tagSha !== candidateSha) {
    throw new Error(tag + ' already targets a different commit; never move release tags');
  }
  if (release) {
    if (release.draft || release.prerelease) {
      throw new Error(tag + ' already has a draft/prerelease; review it manually before publishing');
    }
    return { publish: false, tag, reason: 'stable release already exists' };
  }
  for (const previous of releases) {
    if (previous.draft || previous.prerelease || !/^v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/.test(previous.tag_name)) continue;
    if (compareStableVersions(previous.tag_name.slice(1), version) > 0) {
      throw new Error('A newer stable release already exists: ' + previous.tag_name);
    }
  }
  if (!latestMainPushPassed(validateRuns, candidateSha) ||
      !latestMainPushPassed(codeqlRuns, candidateSha)) {
    return { publish: false, tag, reason: 'awaiting successful Validate and CodeQL on exact main SHA' };
  }
  return { publish: true, tag, sha: candidateSha };
}

async function optionalGet(api, path) {
  try { return await api.request('GET', path); }
  catch (error) { if (error.status === 404) return null; throw error; }
}

async function tagCommit(api, tag) {
  const ref = await optionalGet(api, 'git/ref/tags/' + tag);
  if (!ref) return null;
  let object = ref.object;
  for (let depth = 0; depth < 3 && object?.type === 'tag'; depth++) {
    const annotated = await api.request('GET', 'git/tags/' + object.sha);
    object = annotated.object;
  }
  if (object?.type !== 'commit') throw new Error('Unsupported tag target for ' + tag);
  return object.sha;
}

export async function planFromGitHub(api, candidateSha, version) {
  const tag = 'v' + version;
  const [main, validateRuns, codeqlRuns, release, releases, tagSha] = await Promise.all([
    api.request('GET', 'git/ref/heads/main'),
    api.list('actions/workflows/validate.yml/runs?event=push&branch=main&head_sha=' + candidateSha, 'workflow_runs'),
    api.list('actions/workflows/codeql.yml/runs?event=push&branch=main&head_sha=' + candidateSha, 'workflow_runs'),
    optionalGet(api, 'releases/tags/' + tag),
    api.list('releases'),
    tagCommit(api, tag),
  ]);
  return assessRelease({
    candidateSha, mainSha: main.object.sha, version, validateRuns, codeqlRuns,
    release, releases, tagSha,
  });
}

async function main() {
  const repo = process.env.GITHUB_REPOSITORY;
  const api = githubClient(repo, process.env.GH_TOKEN);
  const candidateSha = execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim();
  const manifest = JSON.parse(readFileSync('custom_components/salah_timetable/manifest.json', 'utf8'));
  const version = manifest.version;
  const plan = await planFromGitHub(api, candidateSha, version);
  if (process.argv.includes('--assert')) {
    if (!plan.publish || process.env.RELEASE_SHA !== candidateSha || process.env.RELEASE_TAG !== plan.tag) {
      throw new Error('Publication recheck failed: ' + (plan.reason || 'candidate changed'));
    }
  }
  console.log(plan.publish ? 'Ready for stable release ' + plan.tag : 'Skipped ' + plan.tag + ': ' + plan.reason);
  if (process.env.GITHUB_OUTPUT && !process.argv.includes('--assert')) {
    appendFileSync(process.env.GITHUB_OUTPUT,
      'publish=' + plan.publish + '\ntag=' + plan.tag + '\nsha=' + candidateSha + '\n');
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch(error => {
    console.error(error);
    process.exitCode = 1;
  });
}
