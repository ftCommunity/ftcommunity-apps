/*
 * Initialize the connection to the RoboWeb websocket
 * and start Snap! with FT-Robo-Snap blocks preloaded.
 *
 * (c) 2016 Richard Kunze
 *
 * This file is part of FT-Robo-Snap (https://github.com/rkunze/ft-robo-snap)
 *
 * FT-Robo-Snap is free software licensed under the Affero Gnu Public License, either version 3
 * or (at your discretion) any later version.
 */

/*
   global
   SpriteMorph, StageMorph, SnapTranslator, WorldMorph, IDE_Morph,
   SyntaxElementMorph, requestAnimationFrame, MultiArgMorph, localize
   InputSlotMorph, SymbolMorph, newCanvas, Costume, Point, StringMorph,
   Process, MorphicPreferences
*/


function FTRoboSnap() {
    this.dict = {};
    var ide = undefined;

    function init_controller() {
        return {
            is_online : false,
            name : undefined,
            version : undefined,
            mode: "disconnected",
            configuration: {},
            iostate: {},
            changed: {},
            errors: [],
        };
    }

    var controller = init_controller();

    this.controller = function() { return controller; };

    var dummyConnection = {
        send: function() {
            throw FTRoboError(localize('No connection to FT Robo TXT'));
        }
    };

    var status_handlers = {
        "controller": function(data) {
            controller.name = data.name || controller.name;
            controller.version = data.version || controller.version;
            controller.mode = data.mode || controller.mode;
            controller.is_online = controller.mode == "online";
            if (FTRoboSnap.ide) { FTRoboSnap.ide.controlBar.updateLabel(); }
       },
        "iostate": function(data) {
            for (var key in data) {
                var is_changed = (controller.iostate[key] != data[key]);
                controller.iostate[key] = data[key];
                controller.changed[key] |= is_changed;
            }
        },

        "configuration": function(data) {
            controller.configuration = data;
        },
    };

    function handle_status(message) {
        for (var key in message) {
            var action = status_handlers[key];
            if (action) { action(message[key]); }
        }
    }

    var ftroboConnection = dummyConnection;
    function connectFTRoboTXT() {
        var conn = new WebSocket("ws://" + window.location.host + "/control");
        conn.onclose = function() {
            console.log("Lost connection to Robo TXT, reconnecting...");
            controller = init_controller();
            if (FTRoboSnap.ide) { FTRoboSnap.ide.controlBar.updateLabel(); }
            connectFTRoboTXT();
        };
        conn.onopen = function() {
            ftroboConnection = conn;
            if (FTRoboSnap.ide) { FTRoboSnap.ide.controlBar.updateLabel(); }
        };
        conn.onmessage = function(event) {
            var message = JSON.parse(event.data);
            var type = message.reply;
            if (type == "status") {
                handle_status(message);
            } else {
                console.log(message);
                controller.errors.push(message);
            }

        };
    }

    connectFTRoboTXT();

    this.send = function(message, online_mode_required) {
        if (online_mode_required && !controller.is_online) {
            throw new FTRoboError(localize("Controller is offline"));
        }
        ftroboConnection.send(JSON.stringify(message));
    };

    function blockFromInfo(info) {
        if (StageMorph.prototype.hiddenPrimitives[info.selector]) {
            return null;
        }
        var newBlock = SpriteMorph.prototype.blockFromInfo(info.selector, info, true);
        newBlock.isTemplate = true;
        return newBlock;
    }


    function monkeyPatchBlockTemplates(target) {
        var unpatched = target.prototype.blockTemplates;
        return function(category) {
            var blocks = unpatched.apply(this, arguments);
            var my_blocks = FTRoboSnap.blocks[category];
            if (my_blocks) {
                blocks.push("=");
                Array.prototype.push.apply(blocks, my_blocks.map(blockFromInfo));
            }
            return blocks;
        };
    }

    function monkeyPatchBlocks(target) {
        Object.keys(FTRoboSnap.blocks).forEach(function(category){
            FTRoboSnap.blocks[category].forEach(function(spec){
                target.prototype.blocks[spec.selector] = spec;
            });
        });
    }

    var original_initblocks = SpriteMorph.prototype.initBlocks;
    SpriteMorph.prototype.initBlocks = function() {
        original_initblocks.apply(this, arguments);
        monkeyPatchBlocks(SpriteMorph);
    };

    var original_createControlBar = IDE_Morph.prototype.createControlBar;
    IDE_Morph.prototype.createControlBar = function() {
        original_createControlBar.apply(this, arguments);
        var myself = this;
        this.controlBar.updateLabel = function () {
            var padding = 5;
            var suffix = myself.world().isDevMode ?
                    ' - ' + localize('development mode') : '';
            if (controller.mode == "disconnected") {
                suffix += " - disconnected";
            } else {
                suffix += " - connected to " + controller.name + " v" + controller.version;
            }
            if (this.label) {
                this.label.destroy();
            }
            if (myself.isAppMode) {
                return;
            }

            this.label = new StringMorph(
                (myself.projectName || localize('untitled')) + suffix,
                14,
                'sans-serif',
                true,
                false,
                false,
                MorphicPreferences.isFlat ? null : new Point(2, 1),
                myself.frameColor.darker(myself.buttonContrast)
            );
            this.label.color = myself.buttonLabelColor;
            this.label.drawNew();
            this.add(this.label);
            this.label.setCenter(this.center());
            this.label.setLeft(this.settingsButton.right() + padding);
        };
    };

    SpriteMorph.prototype.blockTemplates = monkeyPatchBlockTemplates(SpriteMorph);
    StageMorph.prototype.blockTemplates = monkeyPatchBlockTemplates(StageMorph);

    var unpatchedLabelPart = SyntaxElementMorph.prototype.labelPart;
    SyntaxElementMorph.prototype.labelPart = function (spec) {
        var spec_or_constructor = FTRoboSnap.labelspecs[spec];
        if (typeof(spec_or_constructor) === 'function') {
            return spec_or_constructor(spec);
        } else if (typeof(spec_or_constructor) === 'string') {
            spec = spec_or_constructor;
        }
        return unpatchedLabelPart.apply(this, arguments);
    };
}

function FTRoboError(message) {
    this.message = message;
    if ("captureStackTrace" in Error)
        Error.captureStackTrace(this, FTRoboError);
    else
        this.stack = (new Error()).stack;
}

FTRoboError.prototype = Object.create(Error.prototype);
FTRoboError.prototype.name = "FT Robo Error";
FTRoboError.prototype.constructor = FTRoboError;

// our specialized label part specs definitions. The entries
// may be either functions that create the appropriate morph, or
// strings to translate a custom label spec to a standard label spec
FTRoboSnap.prototype.labelspecs = function() {
    var labelspecs = {
        "$ftrobo"           : ftlogo,
        "%ftroboInput"      : choice(false, enumchoice("I", 8), "I1"),
        "%ftroboOutput"     : choice(false, enumchoice("O", 8), "O1"),
        "%ftroboCounter"    : choice(false, enumchoice("C", 4), "C1"),
        "%ftroboMotor"      : choice(false, enumchoice("M", 4), "M1"),
        "%ftroboMotorList"  : function(){ return new MultiArgMorph("%ftroboMotor", null, 1); },
        "%ftroboCounterList"  : function(){ return new MultiArgMorph("%ftroboCounter", null, 1); },
        "%ftroboInputList"  : function(){ return new MultiArgMorph("%ftroboInput", null, 1); },
        "%ftroboInputOrCounterList"  : function(){ return new MultiArgMorph("%ftroboInputOrCounter", null, 1); },
        "%ftroboMotorOrNone": choice(false, enumchoice("M", 4), ""),
        "%ftroboMotorOrOutput": choice(false, enumchoice("M", 4, {"O1/O2":"O1/O2", "O3/O4":"O3/O4", "O5/O6":"O5/O6","O7/O8":"O7/O8"}), "M1"),
        "%ftroboInputOrCounter": choice(false, enumchoice("C", 4, enumchoice("I", 8)), "I1"),
        "%ftroboWatchAll": choice(false, enumchoice("M", 4, enumchoice("C", 4, enumchoice("I", 8))), "I1"),
        "%ftroboOutputValue": choice(true, {'0 (off)' : '0', '512 (max)': 512}, 0),
        "%ftroboMotorValue" : choice(true, {'+512 (forward)' : 512, '0 (stop)': '0', '-512 (back)' : -512}, 0),
        "%ftroboSteps"      : function() { var r = new InputSlotMorph(null, true); r.setContents('\u221e'); return r; },
        "%ftroboMode"       : choice(false, { "online" : "online", "offline" : "offline"}, "online"),
        "%ftroboMotorOrOutputList": function(){ return new MultiArgMorph("%ftroboMotorOrOutput"); },
    };

    // "ft" logo image
    var ftlogo_costume = undefined;
    var img = new Image();
    img.onload = function () {
        var canvas = newCanvas(new Point(img.width, img.height));
        canvas.getContext('2d').drawImage(img, 0, 0);
        ftlogo_costume = new Costume(canvas, "ft");
    };
    img.src = "ft.png";
    function ftlogo() {
        return ftlogo_costume ? new SymbolMorph(ftlogo_costume, 12) : new StringMorph("ft");
    }

    // private helper functions
    function choice(editable, choices, initial, numeric) {
        return function() {
        var part = new InputSlotMorph(
            null,
            typeof(initial) == 'number',
            choices,
            !editable
        );
        if (typeof(initial) !== 'undefined') {
            part.setContents(initial);
        }
        return part;
    }}
    function enumchoice(prefix, n, data) {
        var result = data || {};
        for (var i = 1; i <= n; i++) {
            var value = prefix + i;
            result[value] = value;
        }
        return result;
    }

    return labelspecs;
}();


// FTRoboSnap block definitions and implementations.
// A block definition is an object with the properties
// * id: the selector (=id) of this block. Will be prefixed with
//   "ftrobo" for patching the imp into SpriteMorph/StageMorph/Process
// * type: the type of the block: "command", "predicate", "reporter" ...
// * spec: the block spec. Will be prefixed with "$ftrobo " before being
//         patched into SpriteMorph.blocks
// * defaults: the parameter defaults for the block. Optional
// * impl: the block implementation funtion.
// * category: the category for the block. Optional, defaults to "other"
// * palette: the palette where the block will be placed. Optional, defaults
//            to the category of the block (or to the "variables" palette
//            if category is "other")
//
// block specs will appear in their respective palette in the same order as they
// appear in the FTRoboSnap.blockdefs list.
FTRoboSnap.prototype.blockdefs = [
{
    id: "SetOutput", category: "motion", type: "command",
    spec: "set %ftroboOutput to %ftroboOutputValue",
    defaults: ["O1", null],
    impl: function(output, value) {
        if (!FTRoboSnap.controller().configuration[output]) {
            throw new FTRoboError(localize("Output is not enabled"));
        }
        var msg = { request: "set" };
        msg[output] = value;
        FTRoboSnap.send(msg, true);
    }
},
{
    id: "SetSpeed", category: "motion", type: "command",
    spec: "set speed of %ftroboMotor to %ftroboMotorValue",
    defaults: ["M1", null],
    impl: function(motor, value) {
        if (!FTRoboSnap.controller().configuration[motor]) {
            throw new FTRoboError(localize("Output is not enabled"));
        }
        if (this.ftroboIsMotorOn(motor)) {
            var msg = { request: "set" };
            msg[motor] = { speed: value };
            FTRoboSnap.send(msg, true);
        }
    }
},
{
    id: "SetMotor", category: "motion", type: "command",
    spec: "run %ftroboMotorList at speed %ftroboMotorValue %br and stop after %ftroboSteps steps",
    // defaults don't work right with a MultiArgMorph as first input slot...
    impl: function(motors, speed, step) {
        if (motors.contents.length > 2) {
            throw new FTRoboError(localize("Cannot synchronize more than two motors"));
        }
        var motor = motors.contents[0];
        var syncto = motors.contents[1];
        if (!FTRoboSnap.controller().configuration[motor] || (syncto && !FTRoboSnap.controller().configuration[syncto])) {
            throw new FTRoboError(localize("Motor is not enabled"));
        }
        var steps = (step == "" || step == "\u221e") ? "unbounded" : step;
        var msg = { request: "set" };
        msg[motor] = { speed: speed + 0, steps: steps, syncto : syncto };
        FTRoboSnap.send(msg, true);
        FTRoboSnap.controller().iostate[motor] = "on";
        FTRoboSnap.controller().changed[motor] = true;
    }
},
{
    id: "IsMotorOn", category: "sensing", type: "predicate",
    spec: "is motor %ftroboMotor running?",
    defaults: ["M1"],
    impl: function(motor) {
        return FTRoboSnap.controller().iostate[motor] == "on";
    }
},
{
    id: "IsSwitchClosed", category: "sensing", type: "predicate",
    spec: "is switch %ftroboInput on?",
    defaults: ["I1"],
    impl: function(input) {
        return FTRoboSnap.controller().iostate[input] > 0;
    }
},
{
    id : "CounterValue", category: "sensing", type: "reporter",
    spec: "current value of %ftroboCounter",
    defaults: ["C1"],
    impl: function(counter) {
        return FTRoboSnap.controller().iostate[counter] || 0;
    }
},
{
    id: "InputValue", category: "sensing", type: "reporter",
    spec: "current value of %ftroboInput",
    defaults: ["I1"],
    impl: function(input) {
        return FTRoboSnap.controller().iostate[input] || 0;
    }
},
{
    id: "IsChanged", category: "sensing", type: "predicate",
    spec: "has %ftroboWatchAll changed?",
    defaults: ["I1"],
    impl: function(watch) {
        var result = FTRoboSnap.controller().changed[watch];
        FTRoboSnap.controller().changed[watch] = false;
        return result == true;
    }
},
{
    id: "StopAll", category: "motion", type: "command",
    spec: "turn off all outputs",
    impl: function(input) {
        FTRoboSnap.send({request: "off"});
        FTRoboSnap.controller().iostate = {};
        var changed = FTRoboSnap.controller().changed
        for (var key in changed) {
            changed[key] = true;
        }
    }
},
{
    id: "WatchCounterChanges", category: "other", palette: "variables", type: "command",
    spec: "watch %ftroboCounterList for value changes",
    defaults: ["C1"],
    impl: function(counters) {
        var msg = { request: "notify" };
        for (var idx =0; idx < counters.contents.length; idx++) {
            msg[counters.contents[idx]] = "onchange";
        }
        FTRoboSnap.send(msg);
    }
},
{
    id: "WatchSwitchChanges", category: "other", palette: "variables", type: "command",
    spec: "watch %ftroboInputList for switch state changes",
    defaults: ["I1"],
    impl: function(inputs) {
        var notify = { request: "notify" };
        var config = { request: "configure" };
        for (var idx =0; idx < inputs.contents.length; idx++) {
            config[inputs.contents[idx]] = "digital";
            notify[inputs.contents[idx]] = "onchange";
        }
        FTRoboSnap.send(config);
        FTRoboSnap.send(notify);
    }
},
{
    id: "StopWatching", category: "other", palette: "variables", type: "command",
    spec: "stop watching %ftroboInputOrCounterList",
    defaults: ["I1"],
    impl: function(watched) {
        var msg = { request: "notify" };
        for (var idx =0; idx < watched.contents.length; idx++) {
            msg[watched.contents[idx]] = "off";
        }
        FTRoboSnap.send(msg);
    }
},
{
    id: "SetMode", category: "other", palette: "variables", type: "command",
    spec: "set mode to %ftroboMode",
    defaults: ["online"],
    impl: function(mode) {
        if (mode == FTRoboSnap.controller().mode) {
            if (this.context.startTime) {
                // When this.startTime is set here, we've just succeded in
                // switiching modes. Time do do some housekeeping...
                if (mode == "online") {
                    // Request the current i/o state after switching
                    // from offline to online mode...
                    FTRoboSnap.send({request : "get" });
                } else {
                    // ... and reset the i/o state to "everything off" after
                    // switching to offline mode
                    FTRoboSnap.controller().iostate = {}
                }
            }
            return null;
        }
        if (!this.context.startTime) {
            this.context.startTime = Date.now();
            if (mode == "offline") {
                FTRoboSnap.send({request : "off"});
            }
            FTRoboSnap.send({request : "configure", mode: mode});
        }
        var now = Date.now();
        if ((now - this.context.startTime) >= 5000) {
            // Time out after 5 seconds
            throw new FTRoboError(localize("Failed to set mode to " + mode));
        } else if (((now - this.context.startTime) % 500) < 10 ) {
            // retry twice per second, allowing a fuzz of ~ 10 ms
            FTRoboSnap.send({request : "configure", mode: mode});
        }

        this.pushContext('doYield');
        this.pushContext();
    },
    patch_target: Process.prototype
},
{
    id: "EnableOutput", category: "other", palette: "variables", type: "command",
    spec: "enable output %ftroboMotorOrOutputList",
    defaults: ["M1"],
    impl: function(outputs) {
        if (!this.context.startTime) {
            this.context.startTime = Date.now();
            var conf = { request : "configure", "default": "unused" };
            for (var idx =0; idx < outputs.contents.length; idx++) {
                var key = outputs.contents[idx];
                var conf_value = (key[0]=="M")?"motor":"output";
                var conf_key = FTRoboSnap.output_conf_keys[key];
                var existing_conf = conf[conf_key];
                if (existing_conf && (existing_conf !== conf_value)) {
                    throw new FTRoboError(conf_key + " " + localize("cannot be used as motor and individual outputs at the same time"));
                }
                conf[conf_key] = conf_value;
            }
            FTRoboSnap.controller().configuration.waiting_for_reply = true;
            FTRoboSnap.send(conf);
        } else if (!FTRoboSnap.controller().configuration.waiting_for_reply) {
            return null;
        }
        if ((Date.now() - this.context.startTime) >= 2000) {
            // Time out after 2 seconds
            throw new FTRoboError(localize("Failed to configure outputs"));
        }

        this.pushContext('doYield');
        this.pushContext();
    },
    patch_target: Process.prototype
},
];

FTRoboSnap.prototype.output_conf_keys = {
    "M1": "M1/O1,O2",
    "M2": "M2/O3,O4",
    "M3": "M3/O5,O6",
    "M4": "M4/O7,O8",
    "O1": "M1/O1,O2",
    "O3": "M2/O3,O4",
    "O5": "M3/O5,O6",
    "O7": "M4/O7,O8",
    "O2": "M1/O1,O2",
    "O4": "M2/O3,O4",
    "O6": "M3/O5,O6",
    "O8": "M4/O7,O8",
    "O1/O2": "M1/O1,O2",
    "O3/O4": "M2/O3,O4",
    "O5/O6": "M3/O5,O6",
    "O7/O8": "M4/O7,O8",
}

FTRoboSnap.prototype.blockdefs.map(function(spec) {
    var selector = "ftrobo" + spec.id;
    if (spec.patch_target) {
        spec.patch_target[selector] = spec.impl;
    } else {
        SpriteMorph.prototype[selector] = spec.impl;
        StageMorph.prototype[selector] = spec.impl;
    }
});

FTRoboSnap.prototype.blocks = function() {
    var blocks = {};
    for (var idx in FTRoboSnap.prototype.blockdefs) {
        var def = FTRoboSnap.prototype.blockdefs[idx];
        var palette = def.palette || def.category;
        var specs = blocks[palette];
        if (!specs) {
            specs = [];
            blocks[palette] = specs;
        }
        var spec = {
            selector : "ftrobo" + def.id,
            spec : "$ftrobo " + def.spec,
            category: def.category,
            defaults: def.defaults,
            type: def.type

        };
        specs.push(spec);
        blocks[palette] = specs;
    }
    return blocks;
}();


FTRoboSnap.prototype.monkeyPatchTranslation = function(script) {
    var install_language_handler = script.onload
    var lang = /lang-(..)\.js/.exec(script.src)[1];
    var orig_translation = document.getElementById('language-base');
    var orig_src = '/snap/lang-' + lang + '.js';

    script.onload = undefined;
    if (orig_translation) {
        document.head.removeChild(orig_translation);
    }
    orig_translation = document.createElement('script');
    orig_translation.id = 'language-base';
    orig_translation.onload = function () {
        var target_dict = SnapTranslator.dict[lang];
        var src_dict = FTRoboSnap.dict[lang];
        Object.keys(src_dict).forEach(function(key){
            target_dict[key] = src_dict[key];
        });
        install_language_handler();
    };
    document.head.appendChild(orig_translation);
    orig_translation.src = orig_src;

};

FTRoboSnap = new FTRoboSnap();
SpriteMorph.prototype.initBlocks();

// IDE startup. Copied here from snap.html because I like my JavaScript code
// to reside in .js files...
var world;
window.onload = function () {
    world = new WorldMorph(document.getElementById('world'));
    world.worldCanvas.focus();
    FTRoboSnap.ide = new IDE_Morph();
    FTRoboSnap.ide.openIn(world);
    loop();
};
function loop() {
    requestAnimationFrame(loop);
    world.doOneCycle();
}

