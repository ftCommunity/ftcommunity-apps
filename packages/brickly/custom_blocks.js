// custom block definitions for brickly incl. python code generation
// https://blockly-demo.appspot.com/static/demos/blockfactory/index.html

// json definition of custom blocks
var block_wait = {
  "type": "wait",
  "message0": "wait %1 seconds",
  "args0": [ { "type": "input_value", "name": "seconds", "check": "Number" } ],
  "inputsInline": true,
  "previousStatement": null,
  "nextStatement": null,
  "colour": 290,
  "tooltip": "Pause program execution a given time"
};

var block_on_off = {
  "type": "on_off",
  "message0": "%1",
  "args0": [ {
      "type": "field_dropdown",
      "name": "state",
      "options": [ [ "on", "1" ], [ "off", "0" ] ]
    } ],
  "output": "Boolean",
  "colour": 290,
  "tooltip": "Set and output state"
};

var block_output = {
  "type": "output",
  "message0": "set output %1 %2",
  "args0": [ {
      "type": "field_dropdown",
      "name": "port",
      "options": [
        [ "O1", "0" ], [ "O2", "1" ], [ "O3", "2" ], [ "O4", "3" ],
        [ "O5", "4" ], [ "O6", "5" ], [ "O7", "6" ], [ "O8", "7" ]
      ] },
    {
      "type": "input_value",
      "name": "value",
      "check": "Boolean"
    }
  ],
  "previousStatement": null,
  "nextStatement": null,
  "colour": 290,
  "tooltip": "Set output state on or off"
}

var block_input = {
  "type": "input",
  "message0": "get %1",
  "args0": [
    {
      "type": "field_dropdown",
      "name": "port",
      "options": [
        [ "I1", "0" ], [ "I2", "1" ], [ "I3", "2" ], [ "I4", "3" ],
        [ "I5", "4" ], [ "I6", "5" ], [ "I7", "6" ], [ "I8", "7" ]
      ]
    }
  ],
  "output": "Boolean",
  "colour": 290,
  "tooltip": "Get input state"
}

// generate python code for custom blocks
Blockly.Python['wait'] = function(block) {
    var value_seconds = Blockly.Python.valueToCode(block, 'seconds', Blockly.Python.ORDER_ATOMIC);
   if(!value_seconds) value_seconds = 0;
    return 'time.sleep(%1)\n'.replace('%1', value_seconds);
};

Blockly.Python['on_off'] = function(block) {
    var state = block.getFieldValue('state');
    if(state == "1") code = "True";
    else             code = "False";
    return [code, Blockly.Python.ORDER_NONE];
};

// generate python code for custom blocks
Blockly.Python['output'] = function(block) {
    var port = block.getFieldValue('port');
    var value = Blockly.Python.valueToCode(block, 'value', Blockly.Python.ORDER_ATOMIC);
    return 'setOutput(%1, %2)\n'.replace('%1', port).replace('%2', value);
}

// generate python code for custom blocks
Blockly.Python['input'] = function(block) {
    var port = block.getFieldValue('port');
    // the command itself is commented out and will be replaced by the server with
    // and appropriate call
    code = 'getInput(%1)'.replace('%1', port);
    return [code, Blockly.Python.ORDER_NONE];
}

function custom_blocks_init() {
    // make custom blocks known to blockly
    Blockly.Blocks['wait'] = {
	init: function() { this.jsonInit(block_wait); } };
    Blockly.Blocks['output'] = {
	init: function() { this.jsonInit(block_output); } };
    Blockly.Blocks['input'] = {
	init: function() { this.jsonInit(block_input); } };
    Blockly.Blocks['on_off'] = {
	init: function() { this.jsonInit(block_on_off); } };
}

