/*
function getSelectedText() {
		var text = "";
		if (typeof window.getSelection != "undefined") {
				text = window.getSelection().toString();
				debugger;
		} else if (typeof document.selection != "undefined" && document.selection.type == "Text") {
				debugger;
				text = document.selection.createRange().text;
		}
		return text;
}

function doSomethingWithSelectedText() {
		var selectedText = getSelectedText();
		if (selectedText) {
				alert("Got selected text " + selectedText);
		}
}
document.onmouseup = doSomethingWithSelectedText;
document.onkeyup = doSomethingWithSelectedText;
*/
var comments = [];
var current_id;
// todo this should be a random thing
var current_topic_id = 0;

var popOverSettings = {
		placement: 'bottom',
		container: 'body',
		trigger: 'manual',
		html: true,
		selector: '[rel="popover"]',
		content: function () {
				return $('#popover-content').html();
		}
}
// TODO Make this work with popovers because it would be cooler
//$('body').popover(popOverSettings);

var audios = {};


function pauseAllAudio(){
	for (var audio_id in audios) {
		audios[audio_id].pause();
	}
}

function setTime(curTime, audio_id){
    console.log("Setting time");
	pauseAllAudio();
	audios[audio_id].currentTime = curTime; 
	audios[audio_id].play();
}



function insertAfter( newNode, referenceNode )
{
	referenceNode.parentNode.insertBefore( newNode, referenceNode.nextSibling );
}



function sendComment(comment, endpoint) {
	$.ajax({
	url: endpoint,
	type: "GET",
	data: {text: comment['text'], 
				 words: comment['words'], 
				 audio_key:audio_key,
				 type: comment['type']},
	contentType: "application/json; charset=utf-8",
	success: function(data) { 
			console.log('received response with id: ' + data.result['id']);
			current_id = data.result['id']; 
			}
	});
	return false;
}

function rangeIntersectsNode(range, node) {
	var nodeRange;
	if (range.intersectsNode) {
		return range.intersectsNode(node);
	} else {
		nodeRange = node.ownerDocument.createRange();
		try {
			nodeRange.selectNode(node);
		} catch (e) {
			nodeRange.selectNodeContents(node);
		}
		return range.compareBoundaryPoints(Range.END_TO_START, nodeRange) == -1 &&
			range.compareBoundaryPoints(Range.START_TO_END, nodeRange) == 1;
	}
}

function create(htmlStr) {
		var frag = document.createDocumentFragment(),
				temp = document.createElement('div');
		temp.innerHTML = htmlStr;
		while (temp.firstChild) {
				frag.appendChild(temp.firstChild);
		}
		return frag;
}

function processComment(comment) {
		if (comment['text'] == 'delete') {
				// delete the words
				for (i = 0; i < comment['words'].length; i++) {
						document.getElementById(comment['words'][i]).style.display = 'none';
				}
		}
		if (comment['text'].substring(0, 6) == 'topic:') {
				// collapse the topic 
				topic = comment['text'].substring(6, comment['text'].length)        
				start_element = document.getElementById(comment['words'][0]);
				stop_element = document.getElementById(comment['words'][comment['words'].length - 1]).nextElementSibling;
				div_text = "<div id=" + current_topic_id + " class=\"collapse in\" aria-expanded=\"true\" \>"
				$(start_element).each(function() {
						$(this).add($(this).nextUntil(stop_element)).wrapAll(div_text);
				});
				text = "<br>\n<b>\n <a href=\"#"+current_topic_id+"\" data-toggle=\"collapse\" aria-expanded=\"true\" class=\"\" id=\"" + current_topic_id + "_controller\"> TOPIC:" + topic + "</a></b>\n<br>";
				var fragment = create(text);
				document.body.insertBefore(fragment, document.getElementById(current_topic_id));
				$("#"+current_topic_id).collapse("hide")
				current_topic_id = current_topic_id + 1;
		}
}

function getSelectionText() {
		var text = "";
		if (window.getSelection) {
				text = window.getSelection().toString();
		} else if (document.selection && document.selection.type != "Control") {
				text = document.selection.createRange().text;
		}
		console.log(text);
		return text;
}

function keywordSubmit(form_name) {
	console.log('form submitted');
	var key = $('#' + form_name + '_audio_key');
	key.value = audio_key;
	return true;
}

function clearSelection() {
    if ( document.selection ) {
        document.selection.empty();
    } else if ( window.getSelection ) {
        window.getSelection().removeAllRanges();
    }
}


function getSelectedElementTags() {
		//TODO: there's a bug that makes it so you have to press ok or the prompt 
		// Comes up when it shoudln't
		var range, sel, elmlist, treeWalker, containerElement;
		sel = window.getSelection();
		if (sel.rangeCount > 0) {
				range = sel.getRangeAt(0);
		}

		if (range) {
				containerElement = range.commonAncestorContainer;
				if (containerElement.nodeType != 1) {
						containerElement = containerElement.parentNode;
				}

				treeWalker = window.document.createTreeWalker(
						containerElement,
						NodeFilter.SHOW_ELEMENT,
						function(node) { return rangeIntersectsNode(range, node) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT; },
						false
				);

				elmlist = [];
				if (treeWalker.currentNode.id.substring(0,4) == 'word') {
						elmlist.push(treeWalker.currentNode);
				}
				while (treeWalker.nextNode()) {
						if (treeWalker.currentNode.id.substring(0,4) == 'word') {
								elmlist.push(treeWalker.currentNode);
						}
				}

				console.log(elmlist);
				
				if (getSelectionText().length > 0 && elmlist.length > 0){
						var text = prompt("Enter comment (MAKE SURE YOU PRESS OK):");
						console.log(text);
						var comment = {};
						comment['text'] = text;
						comment['words'] = [];
						for (var i = 0; i < elmlist.length; i++) {
								comment['words'].push(elmlist[i].id);
						}
						console.log(comment);
						sendComment(comment, $SCRIPT_ROOT + '/_comments');
						comment['id'] = current_id;
						processComment(comment)
						comments.push(comment);
				}
				if (elmlist.length > 0) { clearSelection();}

				return elmlist;
		}
}

// TODO: figure out why this is not being captured
/*
$('#keyword').keydown(function(event){
	if (event.keyCode == 13 || event.which == 13) {
		console.log('sending ' + $('#keyword').val());
      $.getJSON($SCRIPT_ROOT + '/_keyword_search', {
        keyword: $('#keyword').val(),
      }, function(data) {
        $("#result").text(data.result);
      });
    } 
});
*/
$('#keyword').submit(function() {
	console.log('form submitted');
	var key = $('form_audio_key');
	key.val(audio_key);
});


document.onmouseup = getSelectedElementTags;
document.onkeyup = getSelectedElementTags
pauseAllAudio();
window.onload = function(){ pauseAllAudio() }
//document.onkeyup = getSelectionText;
