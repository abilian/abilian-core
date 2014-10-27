define(
    'abilian-init-scribe-widget',
    ['jquery',
     'scribe',
     'scribe-plugin-blockquote-command',
     'scribe-plugin-curly-quotes',
     'scribe-plugin-formatter-plain-text-convert-new-lines-to-html',
     'scribe-plugin-heading-command',
     'scribe-plugin-intelligent-unlink-command',
     'scribe-plugin-keyboard-shortcuts',
     'scribe-plugin-link-prompt-command',
     'scribe-plugin-sanitizer',
     'scribe-plugin-smart-lists',
     'scribe-plugin-abilian-toolbar'
    ],
    function (
        $,
        Scribe,
        scribePluginBlockquoteCommand,
        scribePluginCurlyQuotes,
        scribePluginFormatterPlainTextConvertNewLinesToHtml,
        scribePluginHeadingCommand,
        scribePluginIntelligentUnlinkCommand,
        scribePluginKeyboardShortcuts,
        scribePluginLinkPromptCommand,
        scribePluginSanitizer,
        scribePluginSmartLists,
        scribePluginAbilianToolbar) {

        'use strict';

        var defaultAllowedTags = {
            'a': ['href', 'title'],
            'abbr': ['title'],
            'acronym': ['title'],
            'b': true,
            'blockquote': true,
            'br': true,
            'code': true,
            'em': true,
            'h1': true, 'h2': true, 'h3': true, 'h4': true, 'h5': true, 'h6': true,
            'i': true,
            'img': ['src'],
            'li': true,
            'ol': true,
            'strong': true,
            'ul': true,
            'p': ['align'],
            'u': true
        };


        function initWidget(element) {
            var $element = $(element);
            var inputName = element.dataset.name;
            var input = element.querySelector('input[type="hidden"]' +
                                              '[name="' + inputName + '"]');
            var editorEl = element.querySelector('.editor');
            var scribe = new Scribe(editorEl, { allowBlockElements: true });
            var rows = parseInt(element.dataset.rows || 10),
                lineHeight = parseFloat(window.getComputedStyle(element).lineHeight);
            editorEl.style.height = (rows * lineHeight) + "px";
            editorEl.style.overflowX = 'hidden';
            editorEl.style.overflowY = 'auto';

            function updateInput() {
                input.value = scribe.getHTML();
            }
            scribe.on('content-changed', updateInput);

            /**
             * Keyboard shortcuts
             */
            function ctrlKey(event) {
                return event.metaKey || event.ctrlKey;
            };

            var commandsToKeyboardShortcutsMap = Object.freeze({
                bold: function (event) { return ctrlKey(event) && event.keyCode === 66; }, // b
                italic: function (event) { return ctrlKey(event) && event.keyCode === 73; }, // i
                strikeThrough: function (event) { return ctrlKey(event) && event.shiftKey && event.keyCode === 83; } // s
            });

            /**
             * Plugins
             */
            [
                scribePluginBlockquoteCommand(),
                scribePluginHeadingCommand(1),
                scribePluginHeadingCommand(2),
                scribePluginHeadingCommand(3),
                scribePluginIntelligentUnlinkCommand(),
                scribePluginLinkPromptCommand(),
                scribePluginAbilianToolbar(element.querySelector('[role="toolbar"]')),
                scribePluginSmartLists(),
                scribePluginCurlyQuotes(),
                scribePluginKeyboardShortcuts(commandsToKeyboardShortcutsMap)
            ].forEach(scribe.use, scribe);

            // Formatters
            var allowedTags = $element.data('allowedTags');
            if (!allowedTags || allowedTags.length == 0) {
                allowedTags = defaultAllowedTags;
            }
            scribe.use(scribePluginSanitizer({tags: allowedTags}));

            scribe.use(scribePluginFormatterPlainTextConvertNewLinesToHtml());

            if (!scribe.commands['formatBlock']) {
                scribe.commands['formatBlock'] = new scribe.api.Command('formatBlock');
            }
        } //initWidget
       
        Array.prototype.forEach.call(
            document.querySelectorAll('.scribe-widget'), 
            initWidget);
    }
);
