/* datatable: advanced search */

(function(factory) {
	'use strict';
	require(['AbilianNS', 'jquery', 'jquery.dataTables'], factory );
}
(function(Abilian, $) {
    'use strict';

    function defaultDatatableConfig() {
        if (!Abilian.DEBUG) {
            /* deactivate datatable issuing 'alert' on any error in production.
             * It confuses users. */
            $.fn.dataTable.ext.sErrMode = '';
        }
    }
    Abilian.fn.onAppInit(defaultDatatableConfig);

    /* create new filter instance */
    function instantiateFilter(filterType, args) {
        var FilterClass = AdvancedSearchFilters.oFilters[filterType],
            instance = Object.create(FilterClass.prototype);
        FilterClass.apply(instance, args);
        return instance;
    }

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

    //helper function to unescape html
    var tagsToReplace = {
        '&amp;': '&',
        '&lt;': '<',
        '&gt;': '>'
    };

    function replaceTag(tag) {
        return tagsToReplace[tag] || tag;
    }

    function safe_tags_replace(element) {
        var output =  element.text.replace(/&amp;/g, replaceTag);
        output =  output.replace(/&lt;/g, replaceTag);
        output =  output.replace(/&gt;/g, replaceTag);
        return output;
    }

    /*
     * Create an event handler for a filter 'close' button
     */
    function setupCloseButtonHandler(advInstance, instance) {
        function closeFilter(e) {
            e.preventDefault();
            advInstance.unsetFilter(instance.name);
            advInstance.removeFilter(instance.name);
            instance.$container.trigger('redraw.DT');
        }
        return closeFilter;
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
        self.oFilters = {};
        self.oActiveFilters = {};

        /* filters container */
        self.$Container = $('<div class="advanced-search-filters"></div>');
        var filterSelectContainer = $('<div class="row" />'),
            filterSelect = $('<select />'),
            sAddAdvancedFilter = (oDTSettings.oLanguage.sAddAdvancedFilter
                          || 'Add a filter') + '...',
            filtersContainer = $('<div />').attr({'class': 'form-horizontal'});

        filterSelectContainer.append(filterSelect);
        filterSelect.append($('<option value=""></option>'));

        self.$filtersContainer = filtersContainer;
        self.$filterSelect = filterSelect;

        var aoasf_len = oDTSettings.oInit.aoAdvancedSearchFilters.length;
        for (var i = 0; i < aoasf_len; i++) {
            var $criterionContainer = $('<div></div>')
                    .attr({'class': 'criterion form-group'}),
                $labelContainer = $('<div></div>').
                    attr({'class': 'col-xs-12 col-sm-3 control-label'}),
                $filterContainer = $('<div></div>').
                    attr({'class': 'col-xs-12 col-sm-9'}),
                filter = oDTSettings.oInit.aoAdvancedSearchFilters[i],
                args = [].concat([filter.name, filter.label], filter.args),
                instance = instantiateFilter(filter.type, args),
                defaultValue = filter.defaultValue,
                $option = $('<option>' + filter.label + '</option>')
                    .attr({'value': filter.name}),
                $closeButton = $('<button />')
                    .attr({'class': 'close'})
                    .append($('<span />')
                            .attr({'class': 'glyphicon glyphicon-minus'}))
                    .on('click', setupCloseButtonHandler(self, instance));

            instance.type = filter.type;
            instance.unsetValue = filter.unset;

            if (defaultValue !== undefined
                && !Array.isArray(defaultValue)) {
                defaultValue = [defaultValue];
            }
            instance.defaultValue = defaultValue;

            instance.$container = $criterionContainer;
            /* setup criterion container: label, inputs */
            $criterionContainer.hide();
            $criterionContainer.append($labelContainer, $filterContainer);
            $labelContainer.append($closeButton);

            if (instance.label !== '') {
                $labelContainer.append(
                    $('<label>').append(
                        $('<strong />').text(instance.label)));
            }

            $filterContainer.append(instance.getElements());

            self.aFilters.push(instance);
            self.oFilters[filter.name] = instance;
            filterSelect.append($option);
            filtersContainer.append($criterionContainer);
        }

        filterSelect.select2({
            'containerCssClass': 'col-xs-4 col-md-3',
            'placeholder': sAddAdvancedFilter
        });
        filterSelect.on(
            'change',
            function() {
                self.addFilter(this.value);
                $(this).data('select2').clear();
            }
        );
        self.$Container.append(filterSelectContainer, filtersContainer);

        /* datatables events callbacks */
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
                               oDTSettings.oInstance.fnDraw();
                           });
        self.$Container.on('change.DT',
                           'input, select',
                           function() {
                               oDTSettings.oInstance.fnDraw();
                           });
    };

    /**
     * Filters registry
     */
    AdvancedSearchFilters.oFilters = {};

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
     * Add a new active filter
     *
     * @method
     */
    AdvancedSearchFilters.prototype.addFilter = function(filterName) {
        var instance = this.oFilters[filterName];
        if (instance === undefined) {
            return;
        }

        if (this.oActiveFilters[filterName] !== undefined) {
            // filter already active
            return;
        }

        this.oActiveFilters[filterName] = instance;

        /* install default value if possible and necessary: addFilter may be
         * called from stateLoaded() with a value already set by load
         * function */
        if (!hasValueSet(instance)
            && (instance.defaultValue !== undefined)) {
            instance.load(instance.defaultValue);
        }

        instance.$container.show();
        this.$filterSelect
            .find('option[value="' + filterName + '"]')
            .prop('disabled', true);
    };

    /**
     * Clear a filter
     */
    AdvancedSearchFilters.prototype.unsetFilter = function(filterName) {
        var instance = this.oFilters[filterName];
        if (instance === undefined) {
            return;
        }

        var unset = instance.unsetValue;
        if (!Array.isArray(unset)) { unset = [ unset ]; }
        instance.load(unset);
    };

    /**
     * Remove a filter
     *
     * @method
     */
    AdvancedSearchFilters.prototype.removeFilter = function(filterName) {
        var instance = this.oFilters[filterName];
        if (instance === undefined) {
            return;
        }

        if (this.oActiveFilters[filterName] === undefined) {
            // not in active filters
            return;
        }

        delete this.oActiveFilters[filterName];
        instance.$container.hide();
        this.$filterSelect.find('option[value="' + filterName + '"]').
            prop('disabled', null);
    };

    /**
     * Callback to fill server params before ajax request
     */
    AdvancedSearchFilters.serverParamsCallBack = function(event, aoData) {
        var self = event.data.instance;

        function pushFilterValue(filterName) {
            var f = self.oFilters[filterName],
                vals = f.val();

            if (!(vals instanceof Array)) {
                vals = [vals];
            }
            $(vals).each(function() {
                aoData.push({name: f.name, value: this});
            });
        }

        Object.keys(self.oActiveFilters).sort()
              .forEach(pushFilterValue);
    };

    /**
     * Callback to save filters state
     */
    AdvancedSearchFilters.stateSaveParams = function(event, oSettings, oData) {
        var self = event.data.instance;
        oData.oAdvancedSearchFilters = {};
        Object.keys(self.oActiveFilters).forEach(
            function(filterName, idx) {
                var filter = self.oFilters[filterName];
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
                if (filter.load === undefined ||
                    this[filter.name] === undefined) {
                    return;
                }

                filter.load(this[filter.name]);
                var instance = self.oFilters[filter.name];
                if (hasValueSet(instance)) {
                    self.addFilter(filter.name);
                }
            },
            params);

        return true;
    };

    /* setup standard filters */
    AdvancedSearchFilters.oFilters.text = function() {
        function TextFilter(name, label) {
            this.name = name;
            this.label = label;
            this.$input = $('<input />')
                .attr({'type': 'text', 'name': name});
        }

        TextFilter.prototype = {
            'getElements': function () { return this.$input; },
            'val': function() { return [this.$input.val()]; },
            'save': function() { return [this.$input.val()]; },
            'load': function(vals) { this. $input.val(vals[0]); }
        };
        return TextFilter;
    }();

    AdvancedSearchFilters.oFilters.radio = function() {
        function RadioFilter(name, label) {
             var checked = false,
                 arg_len = arguments.length;

            this.name = name;
            this.label = label;
            this.$elements = $('<div></div>');

            for (var i=2; i < arg_len; i++) {
                var arg = arguments[i],
                    id = name + '_' + i,
                    input = $('<input type="radio">')
                        .attr({'id': id,
                               'name': name,
                               'value': arg.value});

                if (!checked && arg.checked) {
                    input.prop('checked', true);
                    checked = true;
                }

                var $label = $('<label></label>')
                        .attr({'class': 'radio-inline', 'for': id})
                        .append(input)
                        .append(document.createTextNode(arg.label));

                this.$elements.append($label);
            }

            if (!checked) {
                this.$elements.children('input').first().prop('checked', true);
            }
        }
        RadioFilter.prototype = {
            'getElements': function () { return this.$elements; },
            'val': function() { return [this.$elements.find('input:checked').val()]; },
            'save': function() { return [this.$elements.find('input:checked').val()]; },
            'load': function(vals) {
                    this.$elements.find('input').each(
                        function() { this.checked = (this.value == vals[0]); }
                    );
            }
        };
        return RadioFilter;
    }();

    AdvancedSearchFilters.oFilters.checkbox = function() {
        function CheckboxFilter(name, label) {
            var checked = false,
                arg_len = arguments.length;

            this.name = name;
            this.label = label;
            this.$elements = $('<div></div>');

            for (var i=2; i < arg_len; i++) {
                var arg = arguments[i],
                    id = name + '_' + i,
                    input = $('<input type="checkbox">')
                        .attr({'id': id,
                               'name': name,
                               'value': arg.value});

                if (!checked && arg.checked) {
                    input.prop('checked', true);
                    checked = true;
                }

                var $label = $('<label></label>')
                        .attr({'class': 'checkbox-inline', 'for': id})
                        .append(input)
                        .append(document.createTextNode(arg.label));

                this.$elements.append($label);
            }

            if (!checked) {
                this.$elements.children('input').first().prop('checked', true);
            }
        }

        function getVal(container) {
            return container.find('input:checked')
                .map(function(){ return $(this).val();} )
                .get();
        }

        CheckboxFilter.prototype = {
            'getElements': function () { return this.$elements; },
            'val': function() { return getVal(this.$elements); },
            'save': function() { return getVal(this.$elements); },
            'load': function(vals) {
                this.$elements.find('input').each(
                    function() {
                        this.checked = (vals.indexOf(this.value) !== -1);
                    }
                );
            }
        };
        return CheckboxFilter;
    }();

    AdvancedSearchFilters.oFilters.select = function() {
        function SelectFilter(name, label, options, multiple) {
            this.name = name;
            this.label = label;
            this.multiple = multiple;
            multiple = multiple || false;

            var s2_options = [],
                $elements = $('<div>'),
                $select = $('<input />')
                    .attr({'id': name,
                           'name': name,
                          'type': 'hidden'});

            this.$elements = $elements;
            this.$select = $select;
            $elements.append($select);

            for (var i=0; i < options.length; i++) {
                var opt = options[i];
                s2_options.push({'id': opt[0], 'text': opt[1]});
            }

            $select.select2({'data': s2_options,
                             'placeholder': multiple ? '' : '...',
                             'multiple': multiple,
                             'allowClear': true,
                             'width': '20em',
                             'max-width': '100%',
                              containerCssClass: 'form-control',
                             'containerCss': {'margin-left': '0.5em'},
                             'formatResult': safe_tags_replace,
                             'formatSelection': safe_tags_replace
                            });
        }

        function getVal() {
            /* jshint validthis: true */
            var val = this.$select.data('select2').val();
            if (!this.multiple && !val.length) {
                val = [];
            }
            return val;
        }


        SelectFilter.prototype = {
            'getElements': function() { return this.$elements; },
            'val': getVal,
            'save': getVal,
            'load': function(vals) {
                this.$select.data('select2').val(vals);
            }
        };
        return SelectFilter;
    }();

    AdvancedSearchFilters.oFilters.selectAjax = function() {
        function SelectAjaxFilter(name, label, ajax_source, multiple) {
            this.name = name;
            this.label = label;
            this.multiple = multiple;
            multiple = multiple || false;

            var s2_options = [],
                $elements = $('<div>'),
                $select = $('<input />')
                    .attr({'id': name,
                           'name': name,
                           'type': 'hidden'});

            this.$elements = $elements;
            this.$select = $select;
            $elements.append($select);

            $select.select2({
                'data': s2_options,
                'placeholder': multiple ? '' : '...',
                'multiple': multiple,
                'allowClear': true,
                'width': '20em',
                'max-width': '100%',
                'containerCssClass': 'form-control',
                'containerCss': {'margin-left': '0.5em'},
                'minimumInputLength': 2,
                'ajax': {
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
            }); // select2
        }

        function getVal() {
            /* jshint validthis: true */
            var val = this.$select.data('select2').val();
            if (!this.multiple && !val.length) {
                val = [];
            }
            return val;
        }

        function saveVal() {
            /* jshint validthis: true */
            var data = this.$select.data('select2').data();

            if (data) {
              if (!this.multiple && !data.length) {
                data = [];
              }
            }
            else {data=null;}

            return data;
        }

        SelectAjaxFilter.prototype = {
            'getElements': function() { return this.$elements; },
            'val': getVal,
            'save': saveVal,
            'load': function(vals) {
                this.$select.data('select2').data(vals);
            }
        };
        return SelectAjaxFilter;
    }();

    AdvancedSearchFilters.oFilters['select-radio'] = function() {
        function SelectRadioFilter(name, label, s2_args /*, radio_args, ... */) {
            /*
             a select box followed by 3 radios (boolean all/True/False)
             s2_args: contains the select2 data
             radio_args...: a radio is created for each param after s2_args
             */
            var checked = false,
                argLen = arguments.length;
            this.name = name;
            this.label = label;
            this.$elements = $('<div class="form-inline">');
            this.multiple = s2_args['multiple'] || false;


            /* create the select*/
            var selectId = name + '-select',
                $select = $('<input />')
                    .attr({'id': selectId,
                           'name': selectId,
                           'type': 'hidden'}),
                s2Label = $('<label></label>')
                    .attr({'class': 'select-inline', 'for': selectId})
                    .append($select);
            //.append(document.createTextNode(name));
            this.$select = $select;
            this.$elements.append(s2Label, $select);

            $select.select2(
                {'data': s2_args['select-data'],
                 'placeholder': (s2_args['select-label'] || ''),
                 'multiple': this.multiple,
                 'allowClear': true,
                 'width': '20em',
                 'max-width': '100%',
                 'containerCssClass': 'form-control',
                 'containerCss': {'margin-left': '0.5em'}
                });
            this.$elements.append("&nbsp;&nbsp;");
            /* create the radios*/
            for (var i=3; i < argLen; i++) {
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

                var radioLabel = $('<label></label>')
                        .attr({'class': 'radio-inline', 'for': id})
                        .append($input)
                        .append(document.createTextNode(arg.label));

                this.$elements.append(radioLabel);
            }


        }

        function getVal() {
            /*
             get value to fill the  /GET : response with the attribute
             return: list(select:id, radio:value)
             */
            /* jshint validthis: true */
            var radioValue = this.$elements.find('input:checked').val(),
                select2Value = this.$select.select2('val');


            if ( select2Value || radioValue !== 'None') {
                return [select2Value, radioValue];
            }
            return [];
        }

        SelectRadioFilter.prototype = {
            'getElements': function () { return this.$elements; },
            'val': getVal,
            'save': getVal,
            'load': function(vals) {
                if (vals.length === 0) { return; }
                this.$elements.find('label input')
                    .first()
                    .prop('checked', true);
                this.$select.select2('val', vals[0]);
            }
        };

        return SelectRadioFilter;
    }();

    AdvancedSearchFilters.oFilters['checkbox-select'] = function() {
        function CheckboxSelectFilter(name, label, args) {
            var self = this;
            this.name = name;
            this.label = label;
            this.$elements = $('<div>');
            this.$input = $('<input type="checkbox">')
                .attr({'id': name,
                       'name': name,
                       'value': name,
                       'checked': 'checked'});

            var select_id = name + '-select',
                $label = $('<label></label>')
                 .attr({'class': 'checkbox-inline', 'for': name})
                 .append(this.$input)
                 .text(args.label);

            this.$elements.append($label);
            this.$select = $('<input />')
                .attr({'id': select_id,
                       'name': select_id,
                       'type': 'hidden'});
            this.$elements.append(this.$select);
            this.$select.select2({'data': args['select-data'],
                                  'placeholder': (args['select-label'] || ''),
                                  'allowClear': true,
                                  'width': '20em',
                                  'max-width': '100%',
                                  'containerCssClass': 'form-control',
                                  'containerCss': {'margin-left': '0.5em'}
                                 });

            this.$input.on('change', function() {
                self.$select.select2('enable', this.checked);
            });
        }

        function getVal() {
            /* jshint validthis: true */
            if (this.$input.get(0).checked) {
                return [this.$select.select2('val') || this.$input.val()];
            }
            return [];
        }

        CheckboxSelectFilter.prototype = {
            'getElements': function () { return this.$elements; },
            'val': getVal,
            'save': getVal,
            'load': function(vals) {
                if (vals.length === 0) { return; }
                this.$input.get(0).setAttribute('checked', true);
                this.$select.select2('val', vals[0]);
            }
        };
        return CheckboxSelectFilter;
    }();

    AdvancedSearchFilters.oFilters.optional_criterions = function() {
        /* legacy filter. Current filtering system makes this one obsolete */
        function OptionalCriterionFilter(name, label) {
            this.name = name;
            this.label = label;
            var self = this,
                argLen = arguments.length,
                options = {};

            this.criterions = {},
            this.$elements = $('<div />')
                .css('margin-bottom', '0.5em');

            var $select = $('<select />')
                    .css('margin-left', '0.5em')
                    .append($('<option />'));

            for (var i=2; i < argLen; i++) {
                var args = arguments[i];
                var $option = $('<option />')
                        .text(args.label)
                        .data(args)
                        .appendTo($select);
                options[args.value] = $option.get(0);
            }

            $select.on(
                'change',
                function(e) {
                    e.preventDefault();
                    if (this.selectedIndex === 0) {
                        /* this is empty option */
                        return;
                    }

                    $(this).children('option:selected')
                        .each(function() { self.installOption(this); });
                    this.selectedIndex = 0;
                });

            this.$elements.append($select);
        }

        function removeCriterion(e) {
            e.preventDefault();
            e.data.$container.remove();
            e.data.$option.show();
            delete e.data.instance.criterions[e.data.value];
            e.data.$container.trigger('redraw.DT');
        }


        function getValues(self) {
            var result = {'selected_filters' : [],
                          'values': {}};

            for (var filterName in self.criterions) {
                result.selected_filters.push(filterName);
                result.values[filterName] = self.criterions[filterName].save();
            }
            return result;
        }

        OptionalCriterionFilter.prototype = {
            'getElements': function () { return this.$elements; },
            'installOption': function (option) {
                var $option = $(option),
                    args = $option.data(),
                    $container = $('<div />');

                $('<button />')
                    .attr({'class': 'close'})
                    .append($('<span />')
                            .attr({'class': 'glyphicon glyphicon-minus'})
                            .text(args.label))
                    .on('click',
                        {'instance': this,
                         'value': args.value,
                         '$option': $option,
                         '$container': $container
                        },
                        removeCriterion)
                    .appendTo($container);
                $('<input />')
                    .attr({'type': 'hidden',
                           'name': this.name,
                           'value': args.value})
                    .appendTo($container);

                args.checked = true;
                var filterName = this.name + '.' + args.value,
                    filterInstance = instantiateFilter(args.type,
                                                       [filterName, '', args]);

                this.criterions[args.value] = filterInstance;
                $option.hide();
                this.$elements.append($container);
            },
            'val': function() {
                return [JSON.stringify(getValues(this))];
            },
            'save': function() {
                return [getValues(this)];
            },
            'load': function(vals) {
                vals = vals[0];
                for (var filterName in vals.values) {
                    if (this.options==null || !this.options[filterName]) {
                        continue;
                    }
                    this.installOption(this.options[filterName]);
                    this.criterions[filterName].load(vals.values[filterName]);
                }
            },
            'hasValueSet': function () {
                /* jshint camelcase: false */
                return getValues(this).selected_filters.length > 0;
            }
        };

        return OptionalCriterionFilter;
    }();

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
