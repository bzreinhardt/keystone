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
        
        if (elmlist.length > 0){
            var text = prompt("Enter comment (MAKE SURE YOU PRESS OK):");
            console.log(text);
            var comment = {};
            comment['text'] = text;
            comment['words'] = [];
            for (var i = 0; i < elmlist.length; i++) {
                comment['words'].push(elmlist[i].id)
            }
            comments.push(comment);
        }
        
        //$(elmlist[0]).popover("show");
        return elmlist;
    }
}

document.onmouseup = getSelectedElementTags;
document.onkeyup = getSelectedElementTags;