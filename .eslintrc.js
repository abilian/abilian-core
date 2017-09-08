module.exports = {
  root: true,
  // https://github.com/feross/standard/blob/master/RULES.md#javascript-standard-style
  extends: 'standard',
  // required to lint *.vue files
  plugins: [
    'html'
  ],
  env: {
    browser: true,
    es6: true,
    amd: true,
  },
  globals: {
    '$': true,
  },
  // add your custom rules here
  rules: {
    'quotes': 'off',
    'semi': ['error', 'always'],
    'comma-dangle': ['error', 'always-multiline'],
    'space-before-function-paren': 'off',
    'camelcase': 'off',
    // TODO
    'eqeqeq': 'off',
    'no-throw-literal': 'off',
    'handle-callback-err': 'off',
    'no-new': 'off',
  },
};
