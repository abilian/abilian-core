/* jshint camelcase: false */
(function(factory) {
    'use strict';
    require(['jquery', 'FileAPI', 'Hogan'], factory);
}
(function($, api, Hogan) {
    'use strict';
    /**
     * File input widget. Uses FileAPI (http://mailru.github.io/FileAPI/)
     */
    var file_item_template = Hogan.compile(
        '<li class="file-item well well-sm">{{ name }} ({{ size }}) '
        + '<a class="close" href="#">&times;</a>'
        + '</li>'
    );

    function FileInput(node, options) {
        var self = this;
        self.root_node = node;
        self.button = node.find('.js-fileapi-wrapper .btn-file');
        var $input = node.find('.js-fileapi-wrapper input');
        self.multiple = Boolean($input.attr('multiple'));
        $input.attr('multiple', null);
        self.input_name = $input.attr('name');
        self.input_model = $input.clone();
        self.list_node = node.find('.selected-files');

        self.button.on('change.fileapi', 'input',
                       {fileinput: self},
                       self.addFiles);
    }

    FileInput.prototype = {
        addFiles: function(evt) {
            var self = evt.data.fileinput;
            var file = api.getFiles(evt)[0];

            if (!self.multiple) {
                self.list_node.empty();
            }

            self.addFileNode(evt.target, file);
        },

        addFileNode: function(input, file) {
            var infos = {
                name: this.sanitizeFilename(file.name),
                type: file.type,
                size: this.humanSize(file.size)
            };
            var el = $(file_item_template.render(infos));
            var $input = $(input).attr({id: null,
                                        name: this.input_name,
                                        'class': 'hide'});
            el.append($input);

            this.list_node.append(el);
            el.find('a.close').on('click', {fileinput: this}, this.removeFileNode);

            if (this.multiple) {
                // create new input element
                this.input_model
                    .clone()
                    .attr({name: null})
                    .appendTo(this.button);
            }
        },

        removeFileNode: function(evt) {
            evt.preventDefault();
            var self = evt.data.fileinput;
            var node = $(evt.target).parent('.file-item');
            node.remove();

            if (!this.multiple) {
                // restore input element
                this.input_model
                    .clone()
                    .attr({name: null})
                    .appendTo(this.button);
            }
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
}));
