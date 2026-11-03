/**
 * Read a fetch Response as JSON and throw a readable error on failure.
 * Hosting platforms return plain-text or HTML error pages (for example
 * "Request Entity Too Large"), and calling res.json() on those used to
 * surface as a confusing "Unexpected token" message.
 */
export async function readJson(res) {
  const body = await res.text();
  let data;
  try {
    data = body ? JSON.parse(body) : {};
  } catch {
    throw new Error(`Server returned ${res.status}: ${body.slice(0, 200) || res.statusText}`);
  }
  if (!res.ok || data.error) {
    throw new Error(data.error || `Server returned ${res.status}`);
  }
  return data;
}
