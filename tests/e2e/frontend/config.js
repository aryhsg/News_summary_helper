// Playwright 測試環境專用的前端設定，在 compose 裡掛載覆蓋正式的 config.js。
// 這樣測試不依賴（也不會洩漏）真實的 API 金鑰；金鑰要跟
// docker-compose.e2e.yml 裡 web 的 INTERNAL_API_KEY 一致。
const API_BASE = location.protocol.startsWith("http")
  ? location.origin
  : "http://localhost:8080";

const API_KEY = "e2e-test-key-not-a-secret";
