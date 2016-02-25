/**
 * @license Copyright (c) 2003-2015, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or http://ckeditor.com/license
 */

CKEDITOR.editorConfig = function( config ) {
    'use strict';
	// Define changes to default configuration here.
	// For complete reference see:
	// http://docs.ckeditor.com/#!/api/CKEDITOR.config
    var Abilian = require('Abilian');
    config.defaultLanguage = Abilian.locale;

    // http://docs.cksource.com/ckeditor_api/symbols/CKEDITOR.config.html#.entities
    // disable accent encoding
    config.entities = false;

    config.skin = 'moono';

    config.extraPlugins = ['autolink',
                           'bootstrapVisibility'];
    config.extraPlugins = config.extraPlugins.join(',');

    config.toolbar = [
		{ name: 'styles', items: [ 'Format' ] },
		{ name: 'basicstyles',
          items: [ 'Bold', 'Italic', 'Underline', '-',
                   'RemoveFormat' ] },
		{ name: 'paragraph',
          items: [ 'NumberedList', 'BulletedList', '-',
                   'Blockquote', '-',
                   'JustifyLeft', 'JustifyCenter', 'JustifyRight', 'JustifyBlock' ] },
		{ name: 'links', items: [ 'Link', 'Unlink'] },
		{ name: 'insert', items: [ 'Image'] },
		{ name: 'clipboard', items: [ 'Paste', 'PasteText', 'PasteFromWord', '-',
                                      'Undo', 'Redo' ] }
	];
	// Set the most common block elements.
	config.format_tags = 'p;h1;h2;h3;pre';

	// Simplify the dialog windows.
	config.removeDialogTabs = 'image:advanced;link:advanced';

    config.allowedContent = {
    'a': { attributes: ['!href', 'title'] },
    'abbr': { attributes: ['title'] },
    'acronym': { attributes: ['title'] },
    'b': {},
    'blockquote': { attributes: ['title'] },
    'br': {},
    'code': { attributes: ['title'] },
    'em': {},
    'i': {},
    'li': {},
    'ol': { attributes: ['title'] },
    'strong': {},
    'ul': { attributes: ['title'] },
    'h1': {},
    'h2': {},
    'h3': {},
    'h4': {},
    'h5': {},
    'h6': {},
    'p': { attributes: ['style'], styles: ['text-align'] },
    'u': {},
    'img': { attributes: ['!src', 'alt', 'title'] }
    };

};
