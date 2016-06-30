/* jshint unused: false */
(function (factory) {
  'use strict';

  define('widget.FileInput',
      ['AbilianWidget', 'jquery', 'FileAPI', 'Hogan'], factory);
}(function (Abilian, $, api, Hogan) {
  'use strict';
  /**
   * File input widget. Uses FileAPI (http://mailru.github.io/FileAPI/)
   */
  var defaults = {
    fileItemTemplate: Hogan.compile(
        '<div id="{{ uid }}" class="file-item">\n' +
        '<span class="file-info">{{ name }} ({{ size }})</span> ' +
        '<a class="close" href="#">&times;</a>' +
        '\n</div>'
    ),
    progressTemplate: '<div class="progress">' +
    '<div class="progress-bar" role="progressbar" ' +
    '     aria-valuenow="0" aria-valuemin="0" ' +
    '     aria-valuemax="100" style="width: 0;">' +
    '</div>' +
    '</div>',
    inputTemplate: '<input type="hidden" name="{{ name }}" />',
    progressBarHeight: '0.2em',
  };

  function FileInput(node, options) {
    var self = this;
    this.currentlyUploaded = {};
    this.options = $.extend({}, defaults, options);
    this.form = node.parent('form');
    this.$input = node.find('.js-fileapi-wrapper input');
    this.$input.attr('disabled', null);
    this.rootNode = node;
    this.button = node.find('.js-fileapi-wrapper .btn-file');
    this.multiple = Boolean(this.$input.attr('multiple'));
    this.$input.attr('multiple', null);
    this.inputName = this.$input.attr('name');
    this.$input.attr('name', null);
    this.listNode = node.find('.selected-files');

    if (node.data('cloned')) {
      this.listNode.empty();
    } else {
      this.listNode.find('.file-item-existing')
          .each(function () {
            self.setupExistingFileNode($(this));
          });
      this.listNode.find('.file-item-uploaded')
          .each(function () {
            self.setupFileNode($(this));
          });
    }

    this.button.on('change', 'input',
        this.addFiles.bind(this));

    this.form.on('submit', this.onFormSubmit.bind(this));
  }

  FileInput.prototype = {
    addFiles: function (evt) {
      var self = this;
      var files = api.getFiles(evt);

      if (!this.multiple) {
        this.listNode.empty();
        files = files.slice(0, 1);
      }

      $(files).each(function () {
        self.addFileNode(evt.target, this);
      });
    },

    setupExistingFileNode: function (node) {
      var button = node.find('button');
      var unwrappedButton = button.get(0);
      var deleted = button.data('deleted');

      if (!unwrappedButton) {
        return;
      }

      unwrappedButton.markerInputElement = $('<input>')
          .attr({
            'type': 'hidden',
            'name': button.data('name'),
            'value': button.data('value'),
          });

      if (deleted) {
        node.append(unwrappedButton.markerInputElement);
      }

      button.on('click', {node: node},
          this.onExistingNodeChange.bind(this));
    },

    setupFileNode: function (node) {
      node.find('a.close')
          .on('click', this.removeFileNode.bind(this));
    },

    addFileNode: function (input, file) {
      var el = this.createFileNode(file);
      this.setupFileNode(el);
      this.listNode.append(el);
      this.triggerUpload(el, file);
    },

    triggerUpload: function (element, file) {
      var uid = api.uid(file);
      this.currentlyUploaded[uid] = true;

      var xhr = api.upload({
        url: Abilian.api.upload.newFileUrl,
        headers: {
          'Accept': 'application/json',
          'X-CSRF-Token': Abilian.csrf_token,
        },
        files: {'file': file},
        progress: this.onFileProgress.bind(this),
        complete: this.onFileComplete.bind(this),
      });
    },

    removeFileNode: function (evt) {
      evt.preventDefault();
      $(evt.target)
          .parent('.file-item')
          .remove();
    },

    createFileNode: function (file) {
      var infos = this.getFileInfos(file);
      var el = $(this.options.fileItemTemplate.render(infos));
      var progress = $(this.options.progressTemplate)
          .css({height: this.options.progressBarHeight});

      el.append(progress);
      return el;
    },

    getElementForFile: function (file) {
      var uid = api.uid(file);
      return $(document.getElementById(uid));
    },

    getFileInfos: function (file) {
      return {
        name: this.sanitizeFilename(file.name),
        type: file.type,
        size: this.humanSize(file.size),
        uid: api.uid(file),
      };
    },

    onExistingNodeChange: function (evt) {
      var button = $(evt.target);
      var markerInputElement = evt.target.markerInputElement;
      var isActive = button.hasClass('active');
      var input = $(evt.data.node).find('input');

      button.toggleClass('active');

      if (!isActive) {
        button.removeClass('btn-default');
        button.addClass('btn-danger');
        button.parent('.file-item').append(markerInputElement);
      } else {
        button.removeClass('btn-danger');
        button.addClass('btn-default');
        $(markerInputElement).remove();
      }
    },

    onFileProgress: function (evt, file, xhr, options) {
      var progress = evt.loaded / evt.total * 100;
      this.getElementForFile(file)
          .find('.progress-bar')
          .css({'width': progress + '%'});
    },

    onFileComplete: function (err, xhr, file, options) {
      var $el = this.getElementForFile(xhr.currentFile);
      var uid = api.uid(xhr.currentFile);

      delete this.currentlyUploaded[uid];

      if (err) {
        $el.remove();
        alert('Echec de l\'envoi du fichier!'); // FIXME: i18n
        return;
      }

      var $input = $('<input>')
          .attr({
            'type': 'hidden',
            'name': this.inputName,
          });
      var result = JSON.parse(xhr.responseText);

      $el.find('.progress').remove();
      $input.val(result.handle);
      $el.append($input);
    },

    onFormSubmit: function (e) {
      if (Object.keys(this.currentlyUploaded).length > 0) {
        e.preventDefault();
        alert('Des fichiers sont en cours d\'envoi'); // FIXME: i18n
      }
    },

    sanitizeFilename: function (filename) {
      return filename.replace(/\\/g, '/').replace(/.*\//, '');
    },

    humanSize: function (size) {
      var unit = 'b';
      var divider = null;

      if (size > api.TB) {
        unit = 'TB';
        divider = api.TB;
      } else if (size > api.GB) {
        unit = 'GB';
        divider = api.GB;
      } else if (size > api.MB) {
        unit = 'MB';
        divider = api.MB;
      } else if (size > api.KB) {
        unit = 'KB';
        divider = api.KB;
      }

      if (divider) {
        size = (size / divider).toFixed(2);
      }

      return size.toString() + unit;
    },

  };

  function createFileInput(options) {
    var element = $(this);
    var widget = new FileInput(element, options);
    element.data('file-input', widget);
    return widget;
  }

  Abilian.registerWidgetCreator('fileInput', createFileInput);

  $.fn.fileInput = function (options) {
    return this.each(
        function () {
          var node = $(this);
          var widget = node.data('file-input');
          if (widget === undefined) {
            widget = new FileInput(node, options);
            node.data('file-input', widget);
          }
          return widget;
        });
  };

  return FileInput;
}));
