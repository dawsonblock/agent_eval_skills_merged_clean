#!/usr/bin/env node

const fs = require("fs");
const os = require("os");
const path = require("path");
const { execFileSync } = require("child_process");

const ROOT = path.resolve(__dirname, "..");
const SKILLS_ROOT = path.join(ROOT, "skills");
const PACKAGES_ROOT = path.join(ROOT, "packages");

function listSkills() {
  const out = [];
  for (const category of fs.readdirSync(SKILLS_ROOT, { withFileTypes: true })) {
    if (!category.isDirectory()) continue;
    const categoryPath = path.join(SKILLS_ROOT, category.name);
    for (const skill of fs.readdirSync(categoryPath, { withFileTypes: true })) {
      if (!skill.isDirectory()) continue;
      const skillPath = path.join(categoryPath, skill.name);
      const skillMd = path.join(skillPath, "SKILL.md");
      if (!fs.existsSync(skillMd)) continue;
      out.push({
        category: category.name,
        name: skill.name,
        sourcePath: skillPath,
      });
    }
  }
  return out;
}

function removeMacArtifacts(dirPath) {
  const entries = fs.readdirSync(dirPath, { withFileTypes: true });
  for (const entry of entries) {
    const full = path.join(dirPath, entry.name);
    if (entry.name === ".DS_Store" || entry.name === "__MACOSX") {
      fs.rmSync(full, { recursive: true, force: true });
      continue;
    }
    if (entry.isDirectory()) {
      removeMacArtifacts(full);
    }
  }
}

function buildOne(skill) {
  const categoryOutDir = path.join(PACKAGES_ROOT, skill.category);
  fs.mkdirSync(categoryOutDir, { recursive: true });
  const zipPath = path.join(categoryOutDir, `${skill.name}.zip`);
  if (fs.existsSync(zipPath)) fs.rmSync(zipPath);

  const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), `skill-pack-${skill.name}-`));
  try {
    const stagingTop = path.join(tmpRoot, skill.name);
    fs.mkdirSync(stagingTop, { recursive: true });
    fs.cpSync(skill.sourcePath, stagingTop, { recursive: true });
    removeMacArtifacts(stagingTop);

    execFileSync("zip", ["-rq", zipPath, skill.name], {
      cwd: tmpRoot,
      stdio: "inherit",
    });

    console.log(`PACKAGED ${skill.category}/${skill.name} -> ${path.relative(ROOT, zipPath)}`);
  } finally {
    fs.rmSync(tmpRoot, { recursive: true, force: true });
  }
}

function main() {
  const skills = listSkills();
  if (skills.length === 0) {
    console.error("No skills found under skills/");
    process.exit(1);
  }
  for (const skill of skills) {
    buildOne(skill);
  }
  console.log(`PASS: packaged ${skills.length} skill ZIP files`);
}

main();
