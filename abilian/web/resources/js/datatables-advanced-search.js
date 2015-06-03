/* datatable: advanced search */
/* jshint camelcase: false */

(function(window, document, undefined) {
(function(factory) {
	"use strict";

	// Using requirejs?
	if ( typeof define === 'function' && define.amd )
	{
		requirejs(['jquery', 'jquery.dataTables'], factory );
	}
	else {
		factory(jQuery);
	}
}
(function($) {
    'use strict';

    function defaultDatatableConfig() {
        if (!Abilian.DEBUG) {
            /* deactivate datatable issuing 'alert' on any error in production.
             * It confuses users. */
            $.fn.dataTable.ext.sErrMode = '';
        }
    }
    defaultDatatableConfig();


    /*
     * Helper to check equality for filter values
     */
    function hasValueSet(filter) {
        var unset = filter.unsetValue,
            val = filter.save();

        if (filter.hasValueSet !== undefined) {
            return filter.hasValueSet();
        }

        if (!Array.isArray(val)) { return true; }

        // ensure unset is an array
        if (!Array.isArray(unset)) { unset = [ unset ]; }

        var length = unset.length;
        if (unset.length != val.length) { return true; }

        for (var key = 0; key < length; key++) {
            if (unset[key] !== val[key]) { return true; }
        }
        return false;
    }

	/**
	* Additional search criterias for DataTable with Ajax source
	*
	* @class AdvancedSearchFilters
	* @constructor
	* @param {object} oDTSettings Settings for the target DataTable.
	*/
    var AdvancedSearchFilters = function(oDTSettings) {
        var self = this;
        self.$Container = null;

        if (!(oDTSettings.oInit.bFilter
              && oDTSettings.oInit.bServerSide
              && oDTSettings.oInit.sAjaxSource
              && 'aoAdvancedSearchFilters' in oDTSettings.oInit
              && oDTSettings.oInit.aoAdvancedSearchFilters.length > 0)) {
            return;
        }

        self.aFilters = [];
        /* filters container */
        self.$Container = $('<div class="advanced-search-filters"></div>');
        self.iconFilterActive = $('<span />', {'class': 'glyphicon glyphicon-filter'});
        var toggle_icon = $('<span />', {'class': 'glyphicon glyphicon-plus'}),
            sAdvSearch = oDTSettings.oLanguage.sAdvancedSearch || 'Advanced Search',
            filters_container = $('<div />');

        self.iconFilterActive.hide();
        filters_container.hide();

        var toggle = $('<span />')
            .css('cursor', 'pointer')
            .append(sAdvSearch + '&nbsp;')
            .append(toggle_icon)
            .append(self.iconFilterActive)
            .bind('click.DT',
                  {target: filters_container, icon: toggle_icon},
                  AdvancedSearchFilters.toggle);

        self.$Container.append(toggle, filters_container);

        /* create filters */
        var aoasf_len = oDTSettings.oInit.aoAdvancedSearchFilters.length;
        for (var i = 0; i < aoasf_len; i++) {
            var $criterion_container = $('<div></div>').attr({'class': 'criterion row'}),
                filter = oDTSettings.oInit.aoAdvancedSearchFilters[i],
                args = [].concat([filter.name, filter.label], filter.args),
                func = AdvancedSearchFilters.oFilters[filter.type],
                instance = func.apply($criterion_container, args);
            instance.type = filter.type;
            instance.unsetValue = filter.unset;
            self.aFilters.push(instance);
            filters_container.append($criterion_container);
        }

        oDTSettings.oInstance.bind('serverParams', {instance: self},
                                   AdvancedSearchFilters.serverParamsCallBack);
        oDTSettings.oInstance.bind('stateSaveParams', {instance: self},
                                   AdvancedSearchFilters.stateSaveParams);
        oDTSettings.oInstance.bind('stateLoaded', {instance: self},
                                   AdvancedSearchFilters.stateLoaded);

        /* when we bind 'stateLoaded' here, state has already been loaded, in DT
           init.  We need to call the handler
         */
        if (oDTSettings.oLoadedState) {
            AdvancedSearchFilters.stateLoaded({data: {instance: self}},
                                              oDTSettings,
                                              oDTSettings.oLoadedState);
        }
        self.$Container.on('redraw.DT',
                           function() {
                               self.updateFilteringIcon();
                               oDTSettings.oInstance.fnDraw();
                           });
        self.$Container.on('change.DT',
                           'input, select',
                           function() {
                               self.updateFilteringIcon();
                               oDTSettings.oInstance.fnDraw();
                           });
    };

     /* filters registry A filter creates required inputs for filter 'name'; the
      * context is the container for this filter
      * @namespace
      */
     AdvancedSearchFilters.oFilters = {
         "text": function(name, label) {
             var self = this;

             if (label != "") {
                 self.append($('<label />')
                             .attr({'class': 'select inline col-md-3 text-right'})
                             .css('cursor', 'default')
                             .append(
                                 $('<strong />').text(label))
                            );
             }

             var $input = $('<input />')
                 .attr({'type': 'text', 'name': name});
             self.append($input);

             return { 'name': name,
                      'val': function() { return [$input.val()]; },
                      'save': function() { return [$input.val()]; },
                      'load': function(vals) { $input.val(vals[0]); }
             };
         },
         "radio": function(name, label) {
             var self = this;
             var checked = false;
             var len = arguments.length;

             if (label != "") {
                 this.append($('<label />')
                             .attr({'class': 'radio-inline col-md-3 text-right'})
                             .css('cursor', 'default')
                             .append(
                                 $('<strong />').text(label))
                            );
             }

             for (var i=2; i < len; i++) {
                 var arg = arguments[i];
                 var id = name + '_' + i;
                 var input = $('<input type="radio">')
                     .attr({'id': id,
                            'name': name,
                            'value': arg.value});

                 if (!checked && arg.checked) {
                     input.prop('checked', true);
                     checked = true;
                 }

                 var label = $('<label></label>')
                     .attr({'class': 'radio-inline', 'for': id})
                     .append(input)
                     .append(document.createTextNode(arg.label));

                 this.append(label);
             }

             if (!checked) {
                 self.children('input').first().prop('checked', true);
             }

             function get_val() {
                 return [self.find('input:checked').val()];
             }

             return { "name": name,
                      "val": get_val,
                      "save": get_val,
                      "load": function(vals) {
                          self.find('input').each(
                              function() {
                                  this.checked = (this.value == vals[0]);
                              }
                          );
                      }
                    };
         },
         'checkbox': function(name, label) {
             var self = this;
             var len = arguments.length;

             if (label != "") {
                 self.append($('<label />')
                             .attr({'class': 'checkbox-inline col-md-3 text-right'})
                             .css('cursor', 'default')
                             .append(
                                 $('<strong />').text(label))
                            );
             }

             for (var i=2; i < len; i++) {
                 var arg = arguments[i];
                 var id = name + '_' + (i-2);
                 var input = $('<input type="checkbox">')
                     .attr({'id': id,
                            'name': name,
                            'value': arg.value});

                 if (arg.checked) {
                     input.prop('checked', true);
                 }

                 var $label = $('<label></label>')
                     .attr({'class': 'checkbox-inline', 'for': id})
                     .append(input)
                     .append(document.createTextNode(arg.label));

                 self.append($label);
             }

             function get_val() {
                 return self.find('input:checked')
                     .map(function(){return $(this).val();})
                     .get();
             }

             return { 'name': name,
                      'val': get_val,
                      'save': get_val,
                      'load': function(vals) {
                          self.find('input').each(
                              function() {
                                  this.checked = (vals.indexOf(this.value) !== -1);
                              }
                          );
                      }
                    };
         },
         'checkbox-select': function(name, label, args) {
             /* a checkbox with a select box activated only if checkbox is checked */
             var self = this;
             var $input = $('<input type="checkbox">')
                 .attr({'id': name,
                        'name': name,
                        'value': name,
                        'checked': 'checked'});
             var $label = $('<label></label>')
                 .attr({'class': 'checkbox-inline', 'for': name})
                 .append($input)
                 .append(document.createTextNode(args.label));

             self.append($label);

             var select_id = name + '-select';
             var $select = $('<input />')
                 .attr({'id': select_id,
                        'name': select_id,
                        'type': 'hidden'});
             self.append($select);
             $select.select2({'data': args['select-data'],
                              'placeholder': (args['select-label'] || ''),
                              'allowClear': true,
                              'width': '20em',
                              'containerCss': {'margin-left': '0.5em'}
                             });


             $input.on('change', function(e) {
                           $select.select2('enable', this.checked);
                       });

             function get_val() {
                 if ($input.get(0).checked) {
                     return [$select.select2('val') || $input.val()];
                 }
                 return [];
             }

             return {
                 'name': name,
                 'val': get_val,
                 'save': get_val,
                 'load': function(vals) {
                     if (vals.length == 0) { return; }
                     $input.get(0).setAttribute('checked', true);
                     $select.select2('val', vals[0]);
                 }
             };
         },
         'select-radio': function(name, label, s2_args /*, radio_args, ... */) {
             /*
             a select box followed by 3 radios (boolean all/True/False)
             s2_args: contains the select2 data
             radio_args...: a radio is created for each param after s2_args
              */
             var self = this;
             var checked = false;
             var len = arguments.length;

             if (label != "") {
                 self.append($('<label />')
                             .attr({'class': 'select-radio inline col-md-3 text-right'})
                             .css('cursor', 'default')
                             .append($('<strong />').text(label))
                            );
             }
             /* create the select*/
             var select_id = name + '-select';
             var $select = $('<input />')
                 .attr({'id': select_id,
                        'name': select_id,
                        'type': 'hidden'});
             var s2_label = $('<label></label>')
                     .attr({'class': 'select-inline', 'for': select_id})
                     .append($select);
                     //.append(document.createTextNode(name));
             $select.select2({'data': s2_args['select-data'],
                              'placeholder': (s2_args['select-label'] || ''),
                              'allowClear': true,
                              'width': '20em',
                              'containerCss': {'margin-left': '0.5em'}
                             });
             self.append(s2_label);

             /* create the radios*/
             for (var i=3; i < len; i++) {
                 var arg = arguments[i];
                 var id = name + '-radio' +'_' + i;
                 var $input = $('<input type="radio">')
                     .attr({'id': id,
                            'name': name + '-radio',
                            'value': arg.value});

                 if (!checked && arg.checked) {
                     $input.prop('checked', true);
                     checked = true;
                 }

                 var radio_label = $('<label></label>')
                     .attr({'class': 'radio-inline', 'for': id})
                     .append($input)
                     .append(document.createTextNode(arg.label));

                 this.append(radio_label);
             }

             function get_val() {
                 /*
                 get value to fill the  /GET : response with the attribute
                 return: list(select:id, radio:value)
                  */
                 var radio_value = self.find('input:checked').val();
                 var select2_value = $select.select2('val')

                 if ( select2_value || radio_value != 'None') {
                     return [select2_value, radio_value];
                 }
                 return [];
             }

             return {
                 'name': name,
                 'val': get_val,
                 'save': get_val,
                 'load': function(vals) {
                     if (vals.length == 0) { return; }
                     $input.get(0).setAttribute('checked', true);
                     $select.select2('val', vals[0]);
                 }
             };
         },
         'select': function(name, label, options, multiple) {
             var self = this;
             var len = arguments.length;
             multiple = multiple || false;

             if (label != "") {
                 self.append($('<label />')
                             .attr({'class': 'select inline col-md-3 text-right'})
                             .css('cursor', 'default')
                             .append(
                                 $('<strong />').text(label))
                            );
             }
             var $select = $('<input />')
                 .attr({'id': name,
                        'name': name,
                        'type': 'hidden'});
             self.append($select);

             var s2_options = [];
             for (var i=0; i < options.length; i++) {
                 var opt = options[i];
                 s2_options.push({'id': opt[0], 'text': opt[1]});
             }

             $select.select2({'data': s2_options,
                              'placeholder': multiple ? '' : '...',
                              'multiple': multiple,
                              'allowClear': true,
                              'width': '20em',
                              'containerCss': {'margin-left': '0.5em'}
                             });

             function get_val() {
                 var val = $select.data('select2').val();
                 if (!multiple && !val.length) { val = []; }
                 return val;
             }
             return { 'name': name,
                      'val': get_val,
                      'save': get_val,
                      'load': function(vals) {
                          $select.data('select2').val(vals);
                      }
                    };
         },
         'selectAjax': function(name, label, ajax_source, multiple) {
             var self = this;
             multiple = multiple || false;

             if (label != "") {
                 self.append($('<label />')
                             .attr({'class': 'select inline col-md-3 text-right'})
                             .css('cursor', 'default')
                             .append(
                                 $('<strong />').text(label))
                            );
             }
             var $select = $('<input />')
                 .attr({'id': name,
                        'name': name,
                        'type': 'hidden'});
             self.append($select);

             $select.select2({
                              minimumInputLength: 2,
                              containerCssClass: 'form-control',
                              placeholder: multiple ? '' : '...',
                              multiple: multiple,
                              allowClear: true,
                              width: '20em',
                              containerCss: {'margin-left': '0.5em'},
                              ajax: {
                                       url: ajax_source,
                                       dataType: 'json',
                                       quietMillis: 200,
                                       data: function (term, page) {
                                         return { q: term };
                                       },
                                       results: function (data, page) {
                                         return {results: data.results, more: false};
                                       }
                                     }
                             });

             function get_val() {
                 var val = $select.data('select2').val();
                 if (!multiple && !val.length) { val = []; }
                 return val;
             }
             function save_val() {
                 return $select.data('select2').data();
             }

             return { 'name': name,
                      'val': get_val,
                      'save': save_val,
                      'load': function(vals) {
                          $select.data('select2').data(vals);
                      },
                      'hasValueSet': function () {
                        return get_val().length > 0;
                        }
                    };
         },
         'optional_criterions': function(name, label) {
             var self = this,
                 arg_len = arguments.length,
                 criterions = {},
                 options = {};

             var $container = $('<div />')
                 .css('margin-bottom', '0.5em')
                 .append($('<span />').text(label + ':'));

             var $select = $('<select />')
                 .css('margin-left', '0.5em')
                 .append($('<option />'));

             for (var i=2; i < arg_len; i++) {
                 var args = arguments[i];
                 var $option = $('<option />')
                    .text(args.label)
                    .data(args)
                    .appendTo($select);
                 options[args.value] = $option.get(0);
             }

             function installOption(option) {
                 var $option = $(option);
                 var args = $option.data();
                 var $container = $('<div />');
                 $('<button />')
                     .attr({'class': 'close'})
                     .append($('<span />').attr({'class': 'glyphicon glyphicon-remove'}))
                     .on('click', function(e) {
                         e.preventDefault();
                         $container.remove();
                         $option.show();
                         delete criterions[args.value];
                         self.trigger('redraw.DT');
                     })
                     .appendTo($container);
                 $('<input />')
                     .attr({'type': 'hidden',
                            'name': name,
                            'value': args.value})
                     .appendTo($container);

                 var func = AdvancedSearchFilters.oFilters[args.type];
                 var filter_name = name + '.' + args.value;
                 args.checked = true;
                 criterions[args.value] = func.apply($container, [filter_name, '', args]);
                 $option.hide();
                 self.append($container);
             }

             $select.on(
                 'change',
                 function(e) {
                     e.preventDefault();
                     if (this.selectedIndex == 0) {
                         /* this is empty option */
                         return;
                     }

                     $(this).children('option:selected')
                         .each(function() { installOption(this); });
                     this.selectedIndex = 0;
                 });

             $container.append($select);
             self.append($container);

             function get_values() {
                 var result = {'selected_filters' : [],
                               'values': {}};

                 for (var filter_name in criterions) {
                     result.selected_filters.push(filter_name);
                     result.values[filter_name] = criterions[filter_name].save();
                 }
                 return result;
             }

             return {
                 'name': name,
                 'val': function() {
                     return [JSON.stringify(get_values())];
                 },
                 'save': function() {
                     return [get_values()];
                 },
                 'load': function(vals) {
                     vals = vals[0];
                     for (var filter_name in vals.values) {
                         if (!options[filter_name]) {
                             continue;
                         }
                         installOption(options[filter_name]);
                         criterions[filter_name].load(vals.values[filter_name]);
                     }
                 },
                 'hasValueSet': function () {
                     return get_values().selected_filters.length > 0;
                 }
             };
         }
     };

	/**
	* Get the container node of the advanced search filters
	*
	* @method
	* @return {Node} The container node.
	*/
	AdvancedSearchFilters.prototype.getContainer = function() {
		return this.$Container && this.$Container.get(0);
	};

    /**
     * Show/hide filtering icon
     */
    AdvancedSearchFilters.prototype.updateFilteringIcon = function() {
        var isFiltering = false;
        //FIXME: a 'for' loop with a 'break' is enough
        this.aFilters.forEach(
            function(filter, idx) {
                if (hasValueSet(filter)) {
                    isFiltering = true;
                }
            });
        isFiltering ? this.iconFilterActive.show() : this.iconFilterActive.hide();
    };


     /**
      * show / hide filters
      */
     AdvancedSearchFilters.toggle = function(e) {
         var target = e.data.target;
         var icon = e.data.icon;
         var should_show = icon.hasClass('glyphicon-plus');
         var is_visible = target.is(':visible');
         icon.toggleClass('glyphicon-plus', !should_show);
         icon.toggleClass('glyphicon-minus', should_show);

         // if 'is_visible' differ from 'should_show' (logical XOR)
         if ((is_visible || should_show) && !(is_visible && should_show)) {
             target.slideToggle(200);
         }
         e.preventDefault();
     };

     /**
      * Callback to fill server params before ajax request
      */
     AdvancedSearchFilters.serverParamsCallBack = function(event, aoData) {
         var self = event.data.instance;
         for(var i=0; i < self.aFilters.length; i++) {
             var f = self.aFilters[i];
             var vals = f.val();
             if (!(vals instanceof Array)) {
                 vals = [vals];
             }
             $(vals).each(function() { aoData.push({name: f.name, value: this});});
         }
     };

    /**
     * Callback to save filters state
     */
    AdvancedSearchFilters.stateSaveParams = function(event, oSettings, oData) {
        var self = event.data.instance;
        oData.oAdvancedSearchFilters = {};
        self.aFilters.forEach(
            function(filter, idx) {
                if (filter.save === undefined) { return; }
                this[filter.name] = filter.save();
            },
            oData.oAdvancedSearchFilters);
        return true;
    };

    /**
     * Callback to restore filters state
     */
    AdvancedSearchFilters.stateLoaded = function(event, oSettings, oData) {
        var self = event.data.instance,
            params = oData.oAdvancedSearchFilters || {};

        self.aFilters.forEach(
            function(filter, idx) {
                if (filter.load === undefined || this[filter.name] === undefined) {
                    return;
                }
                filter.load(this[filter.name]);
            },
            params);
        self.updateFilteringIcon();
        return true;
    };

	/*
	 * Register a new feature with DataTables
	 */
	if ( typeof $.fn.dataTable === 'function'
         && typeof $.fn.dataTableExt.fnVersionCheck === 'function'
         && $.fn.dataTableExt.fnVersionCheck('1.7.0') ) {

		$.fn.dataTableExt.aoFeatures.push( {
			'fnInit': function( oDTSettings ) {
				var asf = new AdvancedSearchFilters(oDTSettings);
				return asf.getContainer();
			},
			'cFeature': 'F',
			'sFeature': 'AdvancedSearchFilters'
		} );
	} else {
		throw 'Warning: AdvancedSearchFilters requires DataTables 1.7 or greater - www.datatables.net/download';
	}

     /*
      * setup useable href arguments according to current table filters criterions.
      * Used for CRM/Excel export
      */
     var dataTableSetExportArgs = function(e) {
         var tbl = $(e.target).dataTable();
         var settings = tbl.fnSettings();
         var params = tbl._fnAjaxParameters(settings);
         tbl._fnServerParams(params);
         $.data(e.target, 'current-query-args', params);
         return false;
     };
     $.fn.dataTableSetExportArgs = dataTableSetExportArgs;


}));

}(window, document));
