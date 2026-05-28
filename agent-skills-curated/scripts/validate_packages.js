#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const AdmZip = require("adm-zip");

const root = path.resolve(__dirname, "..");
const packagesDir = path.join(root, "packages");
let failed = false;

function fail(zipName, msg) {
  failed = true;
  console.error(`FAIL ${zipName}: ${msg}`);
}

function validateZip(zipPath) {
  const zipName = path.relative(root, zipPath);
  const zip = new AdmZip(zipPath);
  const entries = zip.getEntries().filter((e) => !e.isDirectory);
  const names = entries.map((e) => e.entryName.replace(/\\/g, "/"));
  const topLevels = new Set(names.map((n) => n.split("/")[0]).filter(Boolean));

  if (topLevels.size !== 1) {
    fail(
      zipName,
      `expected exactly one top-level directory, found ${[...topLevels].join(", ")}`,
    );
  }

  const skillFiles = names.filter((n) => n.endsWith("/SKILL.md") || n === "SKILL.md");
  if (skillFiles.length !== 1) {
    fail(
      zipName,
      `expected exactly one SKILL.md, found ${skillFiles.length}: ${skillFiles.join(", ")}`,
    );
  }

  for (const name of names) {
    if (name.includes("__MACOSX")) fail(zipName, `contains __MACOSX: ${name}`);
    if (name.includes("node_modules/")) fail(zipName, `contains node_modules: ${name}`);
    if (name.endsWith(".DS_Store")) fail(zipName, `contains .DS_Store: ${name}`);
    if (name.includes("agent-skills-curated/skills/")) {
      fail(zipName, `contains nested repository path: ${name}`);
    }
  }
}

function walk(dir) {
  if (!fs.existsSync(dir)) return [];
  const out = [];
  for (const item of fs.readdirSync(dir)) {
    const p = path.join(dir, item);
    const stat = fs.statSync(p);
    if (stat.isDirectory()) out.push(...walk(p));
    else if (item.endsWith(".zip")) out.push(p);
  }
  return out;
}

const zips = walk(packagesDir);
if (zips.length === 0) {
  console.error("FAIL: no package ZIPs found");
  process.exit(1);
}

for (const z of zips) {
  validateZip(z);
}

if (failed) process.exit(1);
console.log(`PASS: ${zips.length} package ZIPs valid`);
