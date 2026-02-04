{
  "testEnvironment": "node",
  "testMatch": [
    "**/tests/**/*.test.js"
  ],
  "collectCoverageFrom": [
    "**/services/*.js",
    "**/middleware/*.js",
    "**/utils/*.js",
    "!**/node_modules/**"
  ],
  "coverageDirectory": "coverage",
  "coverageReporters": [
    "text",
    "lcov",
    "html"
  ],
  "setupFilesAfterEnv": [
    "<rootDir>/tests/setup.js"
  ],
  "testTimeout": 30000,
  "verbose": true,
  "forceExit": true
}
