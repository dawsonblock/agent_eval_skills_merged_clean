#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");

const ROOT = path.resolve(__dirname, "..");
const PACKAGES_ROOT = path.join(ROOT, "packages");

function listZipEntries(zipPath) {
  const output = execFileSync("zipinfo", ["-1", zipPath], {
    encoding: "utf-8",
  });
  return output
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

function validateZip(zipPath) {
  const entries = listZipEntries(zipPath);
  const errors = [];

  if (entries.length === 0) {
    errors.push("archive is empty");
    return errors;
  }

  const topDirs = new Set();
  const normalizedSet = new Set();
  let skillMdCount = 0;

  for (const entry of entries) {
    const normalized = entry.replace(/\\/g, "/");
    if (normalizedSet.has(normalized)) {
      errors.push(`duplicate entry: ${normalized}`);
    }
    normalizedSet.add(normalized);

    if (normalized.includes(".DS_Store")) {
      errors.push("contains .DS_Store");
    }
    if (normalized.startsWith("__MACOSX/")) {
      errors.push("contains __MACOSX metadata");
    }
    if (normalized.includes("/node_modules/") || normalized.startsWith("node_modules/")) {
      errors.push("contains node_modules");
    }
    if (normalized.startsWith("agent-skills-curated/") || normalized.startsWith("skills/")) {
      errors.push("contains nested repository path");
    }

    const firstPart = normalized.split("/")[0];
    if (firstPart) {
      topDirs.add(firstPart);
    }

    if (normalized.endsWith("/SKILL.md") || normalized === "SKILL.md") {
      skillMdCount += 1;
    }
  }

  if (topDirs.size !== 1) {
    errors.push(`expected exactly 1 top-level directory, found ${topDirs.size}`);
  }
  if (skillMdCount !== 1) {
    errors.push(`expected exactly 1 SKILL.md, found ${skillMdCount}`);
  }

  return [...new Set(errors)];
}

function findZipFiles(dir) {
  const out = [];
  function walk(current) {
    for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
      const full = path.join(current, entry.name);
      if (entry.isDirectory()) {
        walk(full);
      } else if (entry.isFile() && entry.name.endsWith(".zip")) {
        out.push(full);
      }
    }
  }
  walk(dir);
  return out.sort();
}

function main() {
  if (!fs.existsSync(PACKAGES_ROOT)) {
    console.error("FAIL: packages/ directory does not exist");
    process.exit(1);
  }

  const zips = findZipFiles(PACKAGES_ROOT);
  if (zips.length === 0) {
    console.error("FAIL: no ZIP packages found under packages/");
    process.exit(1);
  }

  let failed = 0;
  for (const zipPath of zips) {
    const rel = path.relative(ROOT, zipPath);
    const errors = validateZip(zipPath);
    if (errors.length === 0) {
      console.log(`PASS ${rel}`);
      continue;
    }

    failed += 1;
    console.log(`FAIL ${rel}`);
    for (const err of errors) {
      console.log(`  - ${err}`);
    }
  }

  if (failed > 0) {
    console.error(`FAIL: ${failed} package(s) invalid`);
    process.exit(1);
  }

  console.log(`PASS: all skill packages valid (${zips.length})`);
}

main();
