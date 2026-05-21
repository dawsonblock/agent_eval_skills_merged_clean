"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.compareScriptCovs = compareScriptCovs;
exports.compareFunctionCovs = compareFunctionCovs;
exports.compareRangeCovs = compareRangeCovs;
/**
 * Compares two script coverages.
 *
 * The result corresponds to the comparison of their `url` value (alphabetical sort).
 */
function compareScriptCovs(a, b) {
    if (a.url === b.url) {
        return 0;
    }
    else if (a.url < b.url) {
        return -1;
    }
    else {
        return 1;
    }
}
/**
 * Compares two function coverages.
 *
 * The result corresponds to the comparison of the root ranges.
 */
function compareFunctionCovs(a, b) {
    return compareRangeCovs(a.ranges[0], b.ranges[0]);
}
/**
 * Compares two range coverages.
 *
 * The ranges are first ordered by ascending `startOffset` and then by
 * descending `endOffset`.
 * This corresponds to a pre-order tree traversal.
 */
function compareRangeCovs(a, b) {
    if (a.startOffset !== b.startOffset) {
        return a.startOffset - b.startOffset;
    }
    else {
        return b.endOffset - a.endOffset;
    }
}
