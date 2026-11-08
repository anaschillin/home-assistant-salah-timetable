/** Ephemeral mosque selection scoped to one connected Home Assistant view. */
const views = new WeakMap();
const fallbackScope = {};

export function selectionScope(host) {
  let current = host;
  while (current) {
    if (current.localName === "hui-view") return current;
    current = current.parentElement || current.getRootNode?.()?.host || null;
  }
  return host?.ownerDocument || globalThis.document || fallbackScope;
}

export function joinSelectionGroup(host, name, initialEntity, onChange) {
  if (typeof name !== "string" || !name.trim()) throw new Error("A selection group name is required");
  const scope = selectionScope(host);
  let groups = views.get(scope);
  if (!groups) { groups = new Map(); views.set(scope, groups); }
  const key = name.trim();
  let group = groups.get(key);
  if (!group) { group = {entity: initialEntity, subscribers: new Set()}; groups.set(key, group); }
  const subscriber = {onChange};
  group.subscribers.add(subscriber);
  let active = true;
  onChange(group.entity);
  return {
    get entity() { return group.entity; },
    publish(entity) {
      if (!active || typeof entity !== "string" || !entity || entity === group.entity) return;
      group.entity = entity;
      for (const member of [...group.subscribers]) if (group.subscribers.has(member)) member.onChange(entity);
    },
    leave() {
      if (!active) return;
      active = false;
      group.subscribers.delete(subscriber);
      if (!group.subscribers.size) { groups.delete(key); if (!groups.size) views.delete(scope); }
    },
  };
}
