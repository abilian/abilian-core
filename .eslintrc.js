module.exports = {
  root: true,
  // See: https://github.com/prettier/eslint-config-prettier
  extends: ["prettier", "plugin:requirejs/recommended"],
  // required to lint *.vue files
  plugins: ["html", "requirejs"],
  env: {
    browser: true,
    es6: true,
  },
  // add your custom rules here
  rules: {
    semi: ["error", "always"],
    curly: "error",
  },
};
