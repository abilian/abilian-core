module.exports = {
  root: true,
  // https://github.com/feross/standard/blob/master/RULES.md#javascript-standard-style
  extends: [
    'standard',
    "plugin:requirejs/recommended",
  ],
  // 'html': required to lint *.vue files
  plugins: [
    'html', 'requirejs'
  ],
  env: {
    browser: true,
    es6: true,
  },
  // add your custom rules here
  rules: {
    // Our own deviations from 'standard'
    'quotes': 'off',
    'semi': ['error', 'always'],
    'comma-dangle': ['error', 'always-multiline'],
    'space-before-function-paren': 'off',
    'camelcase': 'off',
    // TODO: 1 occurrence that seems fishy
    'handle-callback-err': 'off',
    // TODO: 1 occurrence that seems fishy
    // 'no-new': 'off',
  },
};
