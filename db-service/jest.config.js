module.exports = {
  preset: "ts-jest",            // handles TypeScript files
  testEnvironment: "node",      // node environment for server tests
  testMatch: ["**/tests/**/*.test.ts"], // where to find test files
  verbose: true
};