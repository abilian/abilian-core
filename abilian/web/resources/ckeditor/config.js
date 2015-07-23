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
		{ name: 'links', items: [ 'Link', 'Unlink', 'Anchor' ] },
		{ name: 'insert', items: [ 'Image', 'Table' ] },
		{ name: 'clipboard', items: [ 'Paste', 'PasteText', 'PasteFromWord', '-',
                                      'Undo', 'Redo' ] },
		{ name: 'editing', items: [ 'SelectAll' ] },
		{ name: 'tools', items: [ 'Maximize' ] }
	];
	// Set the most common block elements.
	config.format_tags = 'p;h1;h2;h3;pre';

	// Simplify the dialog windows.
	config.removeDialogTabs = 'image:advanced;link:advanced';
};
