/* 
 * To change this template, choose Tools | Templates
 * and open the template in the editor.
 */
var testthing;

CKEDITOR.plugins.add('bootstrapVisibility', {
  icons: false,
    lang: 'en,es,fr,it,ru',
    init: function(editor) {
        var lang = editor.lang.bootstrapVisibility;
		 editor.filter.allow ( {
            textarea: {
                attributes: 'class',
                propertiesOnly: true
            },
            input: {
                attributes: 'class',
                propertiesOnly: true
            },
            select: {
                attributes: 'class',
                propertiesOnly: true
            },
            form: {
                attributes: 'class',
                propertiesOnly: true
            },
            button: {
                attributes: 'class',
                propertiesOnly: true
            },
			div: {
				attributes: 'class',
				propertiesOnly: true
			},
			img: {
				attributes: 'class',
				propertiesOnly: true
			},
			table: {
				attributes: 'class',
				propertiesOnly: true
			}
        }, 'formRequired');
		CKEDITOR.on('dialogDefinition', function(ev) {
            var dialogName = ev.data.name;
            var dialogDefinition = ev.data.definition;
			if(ev.data.definition.contents.length >=3) {
				ev.data.definition.minWidth=460
			}

			if(dialogName == 'checkbox' ||  dialogName == 'textfield' || dialogName == 'radio') {
                dialogDefinition.addContents( {
					id: 'responsiveVisibility',
					label: lang.respTabLabel,
					elements: [
						{
							id: 'respoVisibility',
							type: 'select',
							items: [
								[lang.none, ''],
								[lang.hidden_xs, 'hidden-xs'],
								[lang.hidden_sm, 'hidden-sm'],
								[lang.hidden_md, 'hidden-md'],
								[lang.hidden_lg, 'hidden-lg'],
								[lang.visible_xs_block, 'visible-xs-block'],
								[lang.visible_sm_block, 'visible-sm-block'],
								[lang.visible_md_block, 'visible-md-block'],
								[lang.visible_lg_block, 'visible-lg-block'],
								[lang.visible_xs_inline_block, 'visible-xs-inline-block'],
								[lang.visible_sm_inline_block, 'visible-s--inline-block'],
								[lang.visible_md_inline_block, 'visible-md-inline-block'],
								[lang.visible_lg_inline_block, 'visible-lg-inline-block'],
								[lang.visible_xs_inline, 'visible-xs-inline'],
								[lang.visible_sm_inline, 'visible-sm-inline'],
								[lang.visible_md_inline, 'visible-md-inline'],
								[lang.visible_lg_inline, 'visible-lg-inline']
							],
							label: lang.visibilityLabel,
							setup: function(elem) {
								var value = elem.hasAttribute('class') && tws_getResponsiveVisibility( elem.getAttribute('class'));
								this.setValue(value);
							},
							commit: function(a) {
								var element = a.element;
								var val = this.getValue();
								var classes = tws_removeResponsiveClass(element.getAttribute('class'));
							
								if(classes.length != 'undefined' && classes.length>0) {
									classes = classes + ' ' + val;
								} else {
									classes = val;
								}
								if(classes.length != 'undefined' && classes.length >0) {
									element.setAttribute('class', classes.trim());
								} else {
									element.removeAttribute('class');
								}
							}
						},
						{
							type: 'html',
							html: '<p>'+lang.classDetailsHtml+'</p>'
						}
					]
				});
			}
			else if(dialogName == 'select') {
				dialogDefinition.addContents( {
					id: 'responsiveVisibility',
					label: lang.respTabLabel,
					elements: [
						{
							id: 'respoVisibility',
							type: 'select',
							items: [
								[lang.none, ''],
								[lang.hidden_xs, 'hidden-xs'],
								[lang.hidden_sm, 'hidden-sm'],
								[lang.hidden_md, 'hidden-md'],
								[lang.hidden_lg, 'hidden-lg'],
								[lang.visible_xs_block, 'visible-xs-block'],
								[lang.visible_sm_block, 'visible-sm-block'],
								[lang.visible_md_block, 'visible-md-block'],
								[lang.visible_lg_block, 'visible-lg-block'],
								[lang.visible_xs_inline_block, 'visible-xs-inline-block'],
								[lang.visible_sm_inline_block, 'visible-sm-inline-block'],
								[lang.visible_md_inline_block, 'visible-md-inline-block'],
								[lang.visible_lg_inline_block, 'visible-lg-inline-block'],
								[lang.visible_xs_inline, 'visible-xs-inline'],
								[lang.visible_sm_inline, 'visible-sm-inline'],
								[lang.visible_md_inline, 'visible-md-inline'],
								[lang.visible_lg_inline, 'visible-lg-inline']
							],
							label: lang.visibilityLabel,
							setup: function(name, element) {
                                if(name == 'clear') {
                                    this.setValue('');
                                } else if(name == 'select') {
                                    var value = element.hasAttribute('class') && tws_getResponsiveVisibility( element.getAttribute('class'));
                                    this.setValue(value);
                                }

                            },
							commit: function(element) {
								var val = this.getValue();
								var classes = tws_removeResponsiveClass(element.getAttribute('class'));
							
								if(classes.length != 'undefined' && classes.length>0) {
									classes = classes + ' ' + val;
								} else {
									classes = val;
								}
								if(classes.length != 'undefined' && classes.length >0) {
									element.setAttribute('class', classes.trim());
								} else {
									element.removeAttribute('class');
								}
							}
						},
						{
							type: 'html',
							html: '<p>'+lang.classDetailsHtml+'</p>'
						}
					]
				});
			} else if(dialogName == 'form' || dialogName == 'textarea') {
				dialogDefinition.addContents( {
					id: 'responsiveVisibility',
					label: lang.respTabLabel,
					elements: [
						{
							id: 'respoVisibility',
							type: 'select',
							items: [
								[lang.none, ''],
								[lang.hidden_xs, 'hidden-xs'],
								[lang.hidden_sm, 'hidden-sm'],
								[lang.hidden_md, 'hidden-md'],
								[lang.hidden_lg, 'hidden-lg'],
								[lang.visible_xs_block, 'visible-xs-block'],
								[lang.visible_sm_block, 'visible-sm-block'],
								[lang.visible_md_block, 'visible-md-block'],
								[lang.visible_lg_block, 'visible-lg-block'],
								[lang.visible_xs_inline_block, 'visible-xs-inline-block'],
								[lang.visible_sm_inline_block, 'visible-sm-inline-block'],
								[lang.visible_md_inline_block, 'visible-md-inline-block'],
								[lang.visible_lg_inline_block, 'visible-lg-inline-block'],
								[lang.visible_xs_inline, 'visible-xs-inline'],
								[lang.visible_sm_inline, 'visible-sm-inline'],
								[lang.visible_md_inline, 'visible-md-inline'],
								[lang.visible_lg_inline, 'visible-lg-inline']
							],
							label: lang.visibilityLabel,
                            setup: function(element) {
								var value = element.hasAttribute('class') && tws_getResponsiveVisibility( element.getAttribute('class'));
								this.setValue(value);
							},
							commit: function(element) {
								var val = this.getValue();
								var classes = tws_removeResponsiveClass(element.getAttribute('class'));
							
								if(classes.length != 'undefined' && classes.length>0) {
									classes = classes + ' ' + val;
								} else {
									classes = val;
								}
								if(classes.length != 'undefined' && classes.length >0) {
									element.setAttribute('class', classes.trim());
								} else {
									element.removeAttribute('class');
								}
							}
						},
						{
							type: 'html',
							html: '<p>'+lang.classDetailsHtml+'</p>'
						}
					]
				});
			} else if(dialogName == 'creatediv' || dialogName == 'editdiv') {
				dialogDefinition.addContents( {
					id: 'responsiveVisibility',
					label: lang.respTabLabel,
					elements: [
						{
							id: 'respoVisibility',
							type: 'select',
							items: [
								[lang.none, ''],
								[lang.hidden_xs, 'hidden-xs'],
								[lang.hidden_sm, 'hidden-sm'],
								[lang.hidden_md, 'hidden-md'],
								[lang.hidden_lg, 'hidden-lg'],
								[lang.visible_xs_block, 'visible-xs-block'],
								[lang.visible_sm_block, 'visible-sm-block'],
								[lang.visible_md_block, 'visible-md-block'],
								[lang.visible_lg_block, 'visible-lg-block'],
								[lang.visible_xs_inline_block, 'visible-xs-inline-block'],
								[lang.visible_sm_inline_block, 'visible-sm-inline-block'],
								[lang.visible_md_inline_block, 'visible-md-inline-block'],
								[lang.visible_lg_inline_block, 'visible-lg-inline-block'],
								[lang.visible_xs_inline, 'visible-xs-inline'],
								[lang.visible_sm_inline, 'visible-sm-inline'],
								[lang.visible_md_inline, 'visible-md-inline'],
								[lang.visible_lg_inline, 'visible-lg-inline']
							],
							label: lang.visibilityLabel,
                            setup: function(element) {
								var value = element.hasAttribute('class') && tws_getResponsiveVisibility( element.getAttribute('class'));
								this.setValue(value);
							},
							commit: function(element) {
								var val = this.getValue();
								var classes = tws_removeResponsiveClass(element.getAttribute('class'));
							
								if(classes.length != 'undefined' && classes.length>0) {
									classes = classes + ' ' + val;
								} else {
									classes = val;
								}
								if(classes.length != 'undefined' && classes.length >0) {
									element.setAttribute('class', classes.trim());
								} else {
									element.removeAttribute('class');
								}
							}
						},
						{
							type: 'html',
							html: '<p>'+lang.classDetailsHtml+'</p>'
						}
					]
				});
			}
			else if(dialogName == 'button') {
				dialogDefinition.addContents( {
					id: 'responsiveVisibility',
					label: lang.respTabLabel,
					elements: [
						{
							id: 'respoVisibility',
							type: 'select',
							items: [
								[lang.none, ''],
								[lang.hidden_xs, 'hidden-xs'],
								[lang.hidden_sm, 'hidden-sm'],
								[lang.hidden_md, 'hidden-md'],
								[lang.hidden_lg, 'hidden-lg'],
								[lang.visible_xs_block, 'visible-xs-block'],
								[lang.visible_sm_block, 'visible-sm-block'],
								[lang.visible_md_block, 'visible-md-block'],
								[lang.visible_lg_block, 'visible-lg-block'],
								[lang.visible_xs_inline_block, 'visible-xs-inline-block'],
								[lang.visible_sm_inline_block, 'visible-sm-inline-block'],
								[lang.visible_md_inline_block, 'visible-md-inline-block'],
								[lang.visible_lg_inline_block, 'visible-lg-inline-block'],
								[lang.visible_xs_inline, 'visible-xs-inline'],
								[lang.visible_sm_inline, 'visible-sm-inline'],
								[lang.visible_md_inline, 'visible-md-inline'],
								[lang.visible_lg_inline, 'visible-lg-inline']
							],
							label: lang.visibilityLabel,
                            setup: function(element) {
								var value = element.hasAttribute('class') && tws_getResponsiveVisibility( element.getAttribute('class'));
								this.setValue(value);
							},
							commit: function(elem) {
								var val = this.getValue();
								var element = elem.element;
								var classes = tws_removeResponsiveClass(element.getAttribute('class'));
							
								if(classes.length != 'undefined' && classes.length>0) {
									classes = classes + ' ' + val;
								} else {
									classes = val;
								}
								if(classes.length != 'undefined' && classes.length >0) {
									element.setAttribute('class', classes.trim());
								} else {
									element.removeAttribute('class');
								}
							}
						},
						{
							type: 'html',
							html: '<p>'+lang.classDetailsHtml+'</p>'
						}
					]
				});
			}
			else if(dialogName == 'tableProperties' || dialogName == 'table') {
				dialogDefinition.addContents( {
					id: 'responsiveVisibility',
					label: lang.respTabLabel,
					elements: [
						{
							id: 'respoVisibility',
							type: 'select',
							items: [
								[lang.none, ''],
								[lang.hidden_xs, 'hidden-xs'],
								[lang.hidden_sm, 'hidden-sm'],
								[lang.hidden_md, 'hidden-md'],
								[lang.hidden_lg, 'hidden-lg'],
								[lang.visible_xs_block, 'visible-xs-block'],
								[lang.visible_sm_block, 'visible-sm-block'],
								[lang.visible_md_block, 'visible-md-block'],
								[lang.visible_lg_block, 'visible-lg-block'],
								[lang.visible_xs_inline_block, 'visible-xs-inline-block'],
								[lang.visible_sm_inline_block, 'visible-sm-inline-block'],
								[lang.visible_md_inline_block, 'visible-md-inline-block'],
								[lang.visible_lg_inline_block, 'visible-lg-inline-block'],
								[lang.visible_xs_inline, 'visible-xs-inline'],
								[lang.visible_sm_inline, 'visible-sm-inline'],
								[lang.visible_md_inline, 'visible-md-inline'],
								[lang.visible_lg_inline, 'visible-lg-inline']
							],
							label: lang.visibilityLabel,
                            setup: function(element) {
								var value = element.hasAttribute('class') && tws_getResponsiveVisibility( element.getAttribute('class'));
								this.setValue(value);
							},
							commit: function(hmm,element) {
								var val = this.getValue();
								var classes = tws_removeResponsiveClass(element.getAttribute('class'));
							
								if(classes.length != 'undefined' && classes.length>0) {
									classes = classes + ' ' + val;
								} else {
									classes = val;
								}
								if(classes.length != 'undefined' && classes.length >0) {
									element.setAttribute('class', classes.trim());
								} else {
									element.removeAttribute('class');
								}
							}
						},
						{
							type: 'html',
							html: '<p>'+lang.classDetailsHtml+'</p>'
						}
					]
				});
			}
			else if(dialogName == 'image' || dialogName == 'imagebutton') {
				dialogDefinition.addContents( {
					id: 'responsiveVisibility',
					label: lang.respTabLabel,
					elements: [
						{
							id: 'respoVisibility',
							type: 'select',
							items: [
								[lang.none, ''],
								[lang.hidden_xs, 'hidden-xs'],
								[lang.hidden_sm, 'hidden-sm'],
								[lang.hidden_md, 'hidden-md'],
								[lang.hidden_lg, 'hidden-lg'],
								[lang.visible_xs_block, 'visible-xs-block'],
								[lang.visible_sm_block, 'visible-sm-block'],
								[lang.visible_md_block, 'visible-md-block'],
								[lang.visible_lg_block, 'visible-lg-block'],
								[lang.visible_xs_inline_block, 'visible-xs-inline-block'],
								[lang.visible_sm_inline_block, 'visible-sm-inline-block'],
								[lang.visible_md_inline_block, 'visible-md-inline-block'],
								[lang.visible_lg_inline_block, 'visible-lg-inline-block'],
								[lang.visible_xs_inline, 'visible-xs-inline'],
								[lang.visible_sm_inline, 'visible-sm-inline'],
								[lang.visible_md_inline, 'visible-md-inline'],
								[lang.visible_lg_inline, 'visible-lg-inline']
							],
							label: lang.visibilityLabel,
                            setup: function(hmm, element) {
								var value = element.hasAttribute('class') && tws_getResponsiveVisibility( element.getAttribute('class'));
								this.setValue(value);
							},
							commit: function(hmm,element) {
								var val = this.getValue();
								var classes = tws_removeResponsiveClass(element.getAttribute('class'));
							
								if(classes.length != 'undefined' && classes.length>0) {
									classes = classes + ' ' + val;
								} else {
									classes = val;
								}
								if(classes.length != 'undefined' && classes.length >0) {
									element.setAttribute('class', classes.trim());
								} else {
									element.removeAttribute('class');
								}
							}
						},
						{
							type: 'html',
							html: '<p>'+lang.classDetailsHtml+'</p>'
						}
					]
				});
			}
			else if(dialogName == 'flash') {
				dialogDefinition.addContents( {
					id: 'responsiveVisibility',
					label: lang.respTabLabel,
					elements: [
						{
							id: 'respoVisibility',
							type: 'select',
							items: [
								[lang.none, ''],
								[lang.hidden_xs, 'hidden-xs'],
								[lang.hidden_sm, 'hidden-sm'],
								[lang.hidden_md, 'hidden-md'],
								[lang.hidden_lg, 'hidden-lg'],
								[lang.visible_xs_block, 'visible-xs-block'],
								[lang.visible_sm_block, 'visible-sm-block'],
								[lang.visible_md_block, 'visible-md-block'],
								[lang.visible_lg_block, 'visible-lg-block'],
								[lang.visible_xs_inline_block, 'visible-xs-inline-block'],
								[lang.visible_sm_inline_block, 'visible-sm-inline-block'],
								[lang.visible_md_inline_block, 'visible-md-inline-block'],
								[lang.visible_lg_inline_block, 'visible-lg-inline-block'],
								[lang.visible_xs_inline, 'visible-xs-inline'],
								[lang.visible_sm_inline, 'visible-sm-inline'],
								[lang.visible_md_inline, 'visible-md-inline'],
								[lang.visible_lg_inline, 'visible-lg-inline']
							],
							label: lang.visibilityLabel,
                            setup: function(element,b,c) {
								var value = element.hasAttribute('class') && tws_getResponsiveVisibility( element.getAttribute('class'));
								this.setValue(value);
							},
							commit: function(element,b,c,d) {
								var val = this.getValue();
								var classes = tws_removeResponsiveClass(element.getAttribute('class'));
							
								if(classes.length != 'undefined' && classes.length>0) {
									classes = classes + ' ' + val;
								} else {
									classes = val;
								}
								if(classes.length != 'undefined' && classes.length >0) {
									element.setAttribute('class', classes.trim());
								} else {
									element.removeAttribute('class');
								}
							}
						},
						{
							type: 'html',
							html: '<p>'+lang.classDetailsHtml+'</p>'
						}
					]
				});
			}
		});
		
	}
	
	
});
function isArray(arr) {
    return arr.constructor.toString().indexOf("Array") > -1;
}
function tws_isResponsiveClass(className) {
	var responsiveClassList = new Array(
		'hidden-xs','hidden-sm','hidden-md','hidden-lg',
		'visible-xs-block','visible-sm-block','visible-md-block','visible-lg-block',
		'visible-xs-inline-block','visible-sm-inline-block', 'visible-md-inline-block','visible-lg-inline-block',
		'visible-xs-inline', 'visible-sm-inline','visible-md-inline,','visible-lg-inline'
	);
		
	for(i=0;i<responsiveClassList.length;i++) {
		if(className == responsiveClassList[i]) {
			return true;
		}
	}
	return false;
}
function tws_getResponsiveVisibility(classes) {
	if(classes.length > 0) {
		list = classes.split(' ');
		if(isArray(list)) {
			for(iasd=0; iasd<list.length; iasd++) {
				if(tws_isResponsiveClass(list[iasd])) {
					return list[iasd];
				}
			}
		} else {
			if(tws_isResponsiveClass(list)) {
				return list;
				
			} else {
				return '';
			}
		}
	}
	return '';
}
function tws_removeResponsiveClass(classes) {
	var returnData = '';
	if( classes != null && classes.length>0) {
		list = classes.split(' ');
		if(isArray(list)) {
			for(ib=0;ib<list.length;ib++) {
				if(!tws_isResponsiveClass(list[ib])) {
					returnData = returnData + ' '+list[ib];
				}
			}
		} else {
			returnData = classes;
		}
	}
	return returnData.trim();
}