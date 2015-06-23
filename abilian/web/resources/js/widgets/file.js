/* jshint unused: false */
(function(factory) {
    'use strict';
    define('widget.FileInput',
           ['Abilian', 'jquery', 'FileAPI', 'Hogan'], factory);
}
(function(Abilian, $, api, Hogan) {
    'use strict';
    /**
     * File input widget. Uses FileAPI (http://mailru.github.io/FileAPI/)
     */
    var defaults = {
        fileItemTemplate: Hogan.compile(
            '<div id="{{ uid }}" class="file-item col-xs-12 col-md-6">\n' +
                '{{ name }} ({{ size }}) ' +
                '<a class="close" href="#">&times;</a>' +
                '\n</div>'
        ),
        progressTemplate:
            '<div class="progress">' +
            '<div class="progress-bar" role="progressbar" ' +
            '     aria-valuenow="0" aria-valuemin="0" ' +
            '     aria-valuemax="100" style="width: 0%;">' +
            '</div>' +
            '</div>',
        inputTemplate: '<input type="hidden" name="{{ name }}" />',
        progressBarHeight: '0.2em'
    };

    function FileInput(node, options) {
        this.options = $.extend({}, defaults, options);
        this.$input = node.find('.js-fileapi-wrapper input');
        this.rootNode = node;
        this.button = node.find('.js-fileapi-wrapper .btn-file');
        this.multiple = Boolean(this.$input.attr('multiple'));
        this.$input.attr('multiple', null);
        this.inputName = this.$input.attr('name');
        this.$input.attr('name', null);
        this.listNode = node.find('.selected-files');
        this.button.on('change', 'input',
                       this.addFiles.bind(this));
    }

    FileInput.prototype = {
        addFiles: function(evt) {
            var self = this,
                files = api.getFiles(evt);

            if (!this.multiple) {
                this.listNode.empty();
                files = files.slice(0, 1);
            }

            $(files).each(function () {
                self.addFileNode(evt.target, this);
            });
        },

        addFileNode: function(input, file) {
            var el = this.createFileNode(file);
            this.listNode.append(el);
            el.find('a.close').on('click',
                                  this.removeFileNode.bind(this));
            this.triggerUpload(el, file);
        },

        triggerUpload: function(element, file) {
            var xhr = api.upload({
                url:  Abilian.api.upload.newFileUrl,
                headers: {
                    'Accept': 'application/json',
                    'X-CSRF-Token': Abilian.csrf_token
                },
                files: { 'file': file },
                progress: this.onFileProgress.bind(this),
                complete: this.onFileComplete.bind(this)
            });
        },

        removeFileNode: function(evt) {
            evt.preventDefault();
            $(evt.target)
                .parent('.file-item')
                .remove();
        },

        createFileNode: function(file) {
            var infos = this.getFileInfos(file),
                el = $(this.options.fileItemTemplate.render(infos)),
                progress = $(this.options.progressTemplate)
                    .css({height: this.options.progressBarHeight});

            el.append(progress);
            return el;
        },

        getElementForFile: function(file) {
            var uid = api.uid(file);
            console.info('UID = ', uid, ';  file = ', file);
            return $(document.getElementById(uid));
        },

        getFileInfos: function(file) {
            return {
                name: this.sanitizeFilename(file.name),
                type: file.type,
                size: this.humanSize(file.size),
                uid: api.uid(file)
            };
        },

        onFileProgress: function(evt, file, xhr, options) {
            var progress = evt.loaded/evt.total * 100;
            this.getElementForFile(file)
                .find('.progress-bar')
                .css({'width': progress + '%'});
        },

        onFileComplete: function(err, xhr, file, options) {
            var $el = this.getElementForFile(xhr.currentFile);

            if (err) {
                $el.remove();
                return;
            }

            var $input = $('<input>')
                    .attr({'type': 'hidden',
                           'name': this.inputName}),
                result = JSON.parse(xhr.responseText);

            $el.find('.progress').remove();
            $input.val(result.handle);
            $el.append($input);
        },

        sanitizeFilename: function(filename) {
            return filename.replace(/\\/g, '/').replace(/.*\//, '');
        },

        humanSize: function(size) {
            var unit = 'b', divider = null;
            if (size > api.TB) {
                unit = 'TB'; divider = api.TB;
            } else if (size > api.GB) {
                unit = 'GB'; divider = api.GB;
            } else if (size > api.MB) {
                unit = 'MB'; divider = api.MB;
            } else if (size > api.KB) {
                unit = 'KB'; divider = api.KB;
            }

            if (divider) {
                size = (size / divider).toFixed(2);
            }

            return size.toString() + unit;
        }

    };

    $.fn.fileInput = function(options) {
        return this.each(
            function() {
                var node = $(this);
                var input = node.data('file-input');
                if (input === undefined) {
                    input = new FileInput(node, options);
                    node.data('file-input', input);
                }
                return input;
            });
    };

    return FileInput;
}));
