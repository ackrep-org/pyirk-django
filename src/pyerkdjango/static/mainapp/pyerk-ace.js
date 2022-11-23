var editor = ace.edit("editor");
editor.session.setMode("ace/mode/python");
editor.setTheme("ace/theme/monokai");

async function get_auto_complete_list(){
    const url = "/api/get_auto_complete_list";
    const source = await fetch(url);
    const res = await source.json();

    return res.data
}

// create empty list as fallback
var auto_complete_list = [];

// make the call to the API
(async () => {
    try {
        auto_complete_list = await get_auto_complete_list();
        console.log("api call successful");
    } catch (e) {
        console.log("api call not successful");
    }
    // `text` is not available here
})();

var staticWordCompleter = {
    getCompletions: function(editor, session, pos, prefix, callback) {
        var wordList = auto_complete_list;
        callback(null, wordList.map(function(word) {
            return {
                caption: word,
                value: word,
                meta: "static"
                };
        }));
    }
}


//     editor.getSession().setMode('ace/mode/properties');
var langTools = ace.require("ace/ext/language_tools");
editor.setOptions({
    enableBasicAutocompletion: true
});

langTools.setCompleters([staticWordCompleter]);

editor.focus()

// move cursor to last line
var row = editor.session.getLength() - 1
var column = editor.session.getLine(row).length // or simply Infinity
editor.gotoLine(row + 1, column)



// Redefine CTRL+S

document.onkeydown = function(e) {
    if (e.ctrlKey && e.keyCode === 83) {
        alert('In the future this should trigger the server to save the file via api.');


        return false;
    }
};
