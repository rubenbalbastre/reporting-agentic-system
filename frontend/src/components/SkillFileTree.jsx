import { FileText, Folder } from "lucide-react";

function buildTree(paths) {
  const root = { name: "", path: "", type: "dir", children: new Map() };
  for (const raw of paths) {
    const normalized = String(raw || "").replace(/\/+$/, "");
    if (!normalized) continue;

    const parts = normalized.split("/").filter(Boolean);
    let node = root;
    let acc = "";

    for (let i = 0; i < parts.length; i += 1) {
      const part = parts[i];
      acc = acc ? `${acc}/${part}` : part;
      const isLeaf = i === parts.length - 1;
      const isDir = !isLeaf ? true : String(raw).endsWith("/");

      if (!node.children.has(part)) {
        node.children.set(part, {
          name: part,
          path: acc,
          type: isDir ? "dir" : "file",
          children: new Map(),
        });
      }

      node = node.children.get(part);
      if (isDir) node.type = "dir";
    }
  }
  return root;
}

function sortNodes(nodes) {
  return [...nodes].sort((a, b) => {
    if (a.type !== b.type) return a.type === "dir" ? -1 : 1;
    return a.name.localeCompare(b.name);
  });
}

function NodeList({ node, depth }) {
  const children = sortNodes(node.children.values());
  if (!children.length) return null;

  return (
    <ul className="skill-tree-level" data-depth={depth}>
      {children.map((child) => {
        const isSkillMd = child.type === "file" && child.name.toLowerCase() === "skill.md";
        return (
          <li key={child.path} className={`skill-tree-item ${isSkillMd ? "skill-md" : ""}`}>
            <div className="skill-tree-row" style={{ paddingLeft: `${depth * 14}px` }}>
              {child.type === "dir" ? (
                <Folder size={14} strokeWidth={2} aria-hidden="true" />
              ) : (
                <FileText size={14} strokeWidth={2} aria-hidden="true" />
              )}
              <span>{child.name}</span>
            </div>
            {child.type === "dir" ? <NodeList node={child} depth={depth + 1} /> : null}
          </li>
        );
      })}
    </ul>
  );
}

export default function SkillFileTree({ paths }) {
  const tree = buildTree(Array.isArray(paths) ? paths : []);
  return <NodeList node={tree} depth={0} />;
}
