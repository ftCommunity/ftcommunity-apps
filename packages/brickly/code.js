var workspace = Blockly.inject('blocklyDiv',
			       {media: 'media/',
				toolbox: document.getElementById('toolbox')});
var blocklyDiv = document.getElementById('blocklyDiv');
var blocklyArea = document.getElementById('blocklyArea');

custom_blocks_init();
button_set_state(true, true);
loadCode("./brickly.xml");

function set_lang(code) {
    alert("Set lang to " + code);
}

function display_state(str) {
    document.getElementById("stateDiv").innerHTML = str;
}

// switch between "Run..." and "Stop!" button
function button_set_state(enable, run) {
    but = document.getElementById("button");
    but.disabled = !enable;
    if(enable) {
        if(run) {
            but.innerHTML = "Run...";
            but.onclick = runCode;
        } else {
            but.innerHTML = "Stop!";
            but.onclick = stopCode;
        }
    }
}

// htmlize text received from the code before it's being
// put into a text output
function html_escape(str) {
    return str
        .replace(/&/g, '&amp;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;') 
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}

// display some text output by the code
function display_text(str) {
    var objDiv = document.getElementById("textDiv");
    objDiv.innerHTML += str.replace(/\n/g,'<br />');
    objDiv.scrollTop = objDiv.scrollHeight;
}

// display some system text output by the runtime on server side
function display_text_sys(str) {
//    display_text("<span style='background-color: #e8e8e8'>"+str+"</span>");
} 

// clear the text area
function display_text_clr() {
    document.getElementById("textDiv").innerHTML = "";
}

// start the websocket server
function ws_start(initial) {
    url = "ws://"+document.location.hostname+":9002/";
    // if(initial) display_text_sys("Connecting to " + url + " ...\n");
    
    var ws = new WebSocket(url);
    ws.connected = false;
    
    ws.onmessage = function(evt) {
	// ignore empty messages (which we use to force waiting for client)
	if(evt.data.length) {
            // the message is json encoded
	    console.log("RX:" + evt.data);
            obj = JSON.parse(evt.data);
            if(obj.stdout) display_text("<tt><b>"+html_escape(obj.stdout)+"</b></tt>");
            if(obj.stderr) display_text("<font color='red'><tt><b>"+
					    html_escape(obj.stderr)+"</b></tt></font>");
	    if(obj.highlight) {
		if(obj.highlight == "none") {
		    display_state("Program ended");
		    workspace.highlightBlock();
		} else
		    workspace.highlightBlock(obj.highlight);
	    }
	}
    };
    
    ws.onopen = function(evt) {
	workspace.spinner.stop();
        ws.connected = true;
        display_text_sys("<font color='green'>Connected!</font>\n");
        display_state("Connected");
        button_set_state(true, false);
    };
    
    ws.onerror = function(evt) {
    };
    
    ws.onclose = function(evt) {
        // retry if we never were successfully connected
        if(!ws.connected) {
            display_text_sys("<font color='orange'>.</font>");
            //try to reconnect in 100ms
           setTimeout(function(){ws_start(false)}, 100);
        } else {
            display_text_sys("<font color='red'>Disconnected</font>\n");
            display_state("Disconnected");
            ws.connected = false;
            button_set_state(true, true);
	    workspace.highlightBlock();
        }
    };
};

function stopCode() {
    var objDiv = document.getElementById("textArea");
    workspace.spinner = new Spinner({top:"0%", position:"relative", color: '#fff'}).spin(objDiv)

    var http = new XMLHttpRequest();
    http.open("GET", "./brickly_stop.py?pid="+pid);
    http.setRequestHeader("Content-type", "text/html");
    http.onreadystatechange = function() {
        if (http.readyState == XMLHttpRequest.DONE) {
	    workspace.spinner.stop();
	    
            if (http.status != 200) {
		alert("Error " + http.status + "\n" + http.statusText);
            } else {
		// display_text_sys(http.responseText + "\n");
            }
        }
    }
    http.send();
}

function loadCode(name) {
    var http = new XMLHttpRequest();
    http.open("GET", name);
    http.setRequestHeader("Content-type", "application/xml");
    http.onreadystatechange = function() {
        if (http.readyState == XMLHttpRequest.DONE) {
            if (http.status != 200) {
		if (name != "default.xml") {
		    display_text_sys("Loading default ...\n");
		    loadCode("./default.xml");
		}
            } else {
		var xml = Blockly.Xml.textToDom(http.responseText);
		Blockly.Xml.domToWorkspace(xml, workspace);
            }
        }
    }
    http.send();
}

function runCode() {
    // add highlight information to the code. Make it commented so the code
    // will run on any python setup. If highlighting is wanted these lines
    // need to be uncommented on server side
    Blockly.Python.STATEMENT_PREFIX = '# highlightBlock(%1);\n';
    Blockly.Python.addReservedWords('highlightBlock');
    var code = Blockly.Python.workspaceToCode(workspace);

    // there may be no code at all, this is still valid. Mabe we can do something more
    // useful in this case
    if(code == "")
	alert("No code to be run!")
    else {
	var objDiv = document.getElementById("textArea");
	workspace.spinner = new Spinner({top:"0%", position:"relative", color: '#fff'}).spin(objDiv)

	// prepare gui for running program
	display_text_clr();
	button_set_state(false, true);
	display_state("Connecting ...");

	// Generate Python code and POST it
	var xml = Blockly.Xml.workspaceToDom(workspace);
	var text = Blockly.Xml.domToText(xml);
    
	var http = new XMLHttpRequest();
	http.open("POST", "./brickly_run.py");
	http.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
	http.onreadystatechange = function() {
            if (http.readyState == XMLHttpRequest.DONE) {
		if (http.status != 200) {
		    alert("Error " + http.status + "\n" + http.statusText);
		} else {
		    console.log("RX:" + http.responseText);

		    // try to find PID ...
		    pid = JSON.parse(http.responseText).pid;
		    // display_text_sys("PID: " + pid + "\n");
		    
		    // finally connect to the server
		    setTimeout(function(){ws_start(true)}, 500);
		}
            }
	}
	
	// POST python as well as xml
	http.send('code='+encodeURIComponent(code)+'&text='+encodeURIComponent(text));
	}
}

function resizeTo(element, target) {
    // Compute the absolute coordinates and dimensions of source
    var r_element = element;
    var x = 0;
    var y = 0;
    do {
        x += element.offsetLeft;
        y += element.offsetTop;
        element = element.offsetParent;
    } while (element);

    // Position blocklyDiv over blocklyArea.
    target.style.left = x + 'px';
    target.style.top = y + 'px';
    target.style.width = r_element.offsetWidth + 'px';
    target.style.height = r_element.offsetHeight + 'px';
}

var onresize = function(e) {
    resizeTo(blocklyArea, blocklyDiv);
    resizeTo(textArea, textDiv);
};

// window.addEventListener('resize', onresize, false);
window.addEventListener('resize', onresize, false);
onresize();
Blockly.svgResize(workspace);
