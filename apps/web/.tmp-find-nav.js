const fs = require("fs");
const text = fs.readFileSync(".next/static/chunks/app/(marketing)/page.js", "utf8");
const marker = 'href: "/contact"';
let idx = 0;
let n = 0;
while ((idx = text.indexOf(marker, idx)) !== -1) {
  n += 1;
  console.log("\n#", n, text.slice(idx, idx + 180));
  idx += marker.length;
}
console.log("count", n);
const mapCount = text.split("MARKETING_NAV.map").length - 1;
console.log("maps", mapCount);
