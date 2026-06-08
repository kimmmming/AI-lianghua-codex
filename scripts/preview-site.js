const http = require("http");
const fs = require("fs");
const path = require("path");

const projectRoot = path.resolve(__dirname, "..");
const siteDir = fs.existsSync(path.join(projectRoot, "dist"))
  ? path.join(projectRoot, "dist")
  : path.join(projectRoot, "web");
const port = Number(process.env.PORT || 4173);

const contentTypes = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".svg": "image/svg+xml; charset=utf-8",
};

function safeResolve(requestUrl) {
  const url = new URL(requestUrl, `http://localhost:${port}`);
  const pathname = url.pathname === "/" ? "/index.html" : url.pathname;
  const resolved = path.normalize(path.join(siteDir, pathname));
  if (!resolved.startsWith(siteDir)) {
    return null;
  }
  return resolved;
}

const server = http.createServer((request, response) => {
  const filePath = safeResolve(request.url || "/");
  if (!filePath || !fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
    response.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
    response.end("Not found");
    return;
  }

  const extension = path.extname(filePath);
  response.writeHead(200, {
    "Content-Type": contentTypes[extension] || "application/octet-stream",
  });
  fs.createReadStream(filePath).pipe(response);
});

server.listen(port, () => {
  console.log(`Preview server: http://localhost:${port}`);
  console.log(`Serving: ${siteDir}`);
});
