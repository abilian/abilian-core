define('scribe-plugin-abilian-toolbar', [], function () {

    return function (toolbarNode) {
        return function (scribe) {
            var buttons = toolbarNode.querySelectorAll('button[data-command-name]'),
                dropDownsNodes = toolbarNode.querySelectorAll('button[data-toggle="dropdown"]'),
                dropDowns = [];
            
            Array.prototype.forEach.call(dropDownsNodes, function(dropDown) {
                var d = {mainButton: dropDown};
                d.buttons = dropDown.nextElementSibling.querySelectorAll('[data-command-name]');
                d.defaultLabel = dropDown.innerHTML;
                dropDowns.push(d);
            });

            function updateButton(button, selection) {
                // Look for a predefined command.
                var d = button.dataset;
                var command = scribe.getCommand(d.commandName);
                var state = {
                    active: selection.range && command.queryState(),
                    enabled: selection.range && command.queryEnabled()
                };

                // TODO: Do we need to check for the selection?
                // active state
                if (state.active) {
                    button.classList.add("active");
                } else {
                    button.classList.remove("active");
                }

                if (state.enabled) {
                    button.removeAttribute('disabled');
                } else {
                    button.setAttribute('disabled', 'disabled');
                }
                return state;
            }

            function updateUi() {
                var selection = new scribe.api.Selection();

                Array.prototype.forEach.call(buttons, function (button) {
                    updateButton(button, selection);
                });

                dropDowns.forEach(function (dropDown) {
                    var label = null;

                    for (var i=0; i < dropDown.buttons.length; i++) {
                        var button = dropDown.buttons[i];
                        state = updateButton(button, selection);
                        if (state.active) {
                            label = button.innerHTML;
                        }
                    }
                    
                    if (label === null) {
                        label = dropDown.defaultLabel;
                    }
                    dropDown.mainButton.innerHTML = label;
                });
            }

            function runCommand() {
                // Look for a predefined command.
                var command = scribe.getCommand(this.dataset.commandName);
                var value = this.dataset.commandValue;
                /**
                 * Focus will have been taken away from the Scribe instance when
                 * clicking on a button (Chrome will return the focus automatically
                 * but only if the selection is not collapsed. As per: http://jsbin.com/tupaj/1/edit?html,js,output).
                 * It is important that we focus the instance again before executing
                 * the command, because it might rely on selection data.
                 */
                scribe.el.focus();
                command.execute(value);
                /**
                 * Chrome has a bit of magic to re-focus the `contenteditable` when a
                 * command is executed.
                 * As per: http://jsbin.com/papi/1/edit?html,js,output
                 */
            }

            // Keep the state of toolbar buttons in sync with the current selection.
            // Unfortunately, there is no `selectionchange` event.
            scribe.el.addEventListener('keyup', updateUi);
            scribe.el.addEventListener('mouseup', updateUi);

            scribe.el.addEventListener('focus', updateUi);
            scribe.el.addEventListener('blur', updateUi);

            // We also want to update the UI whenever the content changes. This
            // could be when one of the toolbar buttons is actioned.
            scribe.on('content-changed', updateUi);

            function onClick(button) {
                var doRuncommand = runCommand.bind(button);
                return function (e) {
                    e.preventDefault();
                    return doRuncommand();
                };
            }

            Array.prototype.forEach.call(buttons, function (button) {
                var d = button.dataset;
                d.activeCommandName = d.commandName;
                if (d.inactiveIcon) {
                    d.activeIcon = 'fa-' + d.activeIcon;
                    d.inactiveIcon = 'fa-' + d.inactiveIcon;
                }
                button.addEventListener('click', onClick(button));
            });

            function getWidth(element) {
                return parseFloat(window.getComputedStyle(element).width);
            }

            dropDowns.forEach(function (dropDown) {
                var cs= window.getComputedStyle(dropDown.mainButton),
                    maxWidth = parseFloat(cs.width);
                // compute padding; X * fontSize: X unit is 'em'
                var carretPadding = 0.5 * parseFloat(cs.fontSize);

                for (var i=0; i < dropDown.buttons.length; ++i) {
                    var button = dropDown.buttons[i];
                    dropDown.mainButton.innerHTML = button.innerHTML;
                    maxWidth = Math.max(maxWidth, getWidth(dropDown.mainButton));
                    button.addEventListener('click', onClick(button));
                }
                dropDown.mainButton.innerHTML = dropDown.defaultLabel;

                dropDown.mainButton.style.width = maxWidth + + carretPadding + "px";
            });


        };
    };

});
