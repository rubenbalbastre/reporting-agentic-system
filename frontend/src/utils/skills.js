export function isPublishedSkillPath(skillMdPath) {
  const path = String(skillMdPath || "").toLowerCase();
  return path.includes("/skills/") && !path.includes("/skills_drafts/");
}

export function isPublishedSkill(skill) {
  return isPublishedSkillPath(skill?.skill_md_path);
}
