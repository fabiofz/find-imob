import unittest
try:
    import quickjs
except ImportError:
    quickjs = None
from ui_feedback import NAVIGATION_JS

DOM = r'''
globalThis.window=globalThis;
let mutation;
let listener;
let state='notRunning';
let overlay;
let timeoutHandler;
class Element {
 constructor(kind='') { this.kind=kind; this.checked=false; this.dataset={}; this.attributes={}; }
 setAttribute(k,v){this.attributes[k]=v;}
 getAttribute(k){return this.attributes[k];}
 removeAttribute(k){delete this.attributes[k];}
 appendChild(node){if(node.id==='findimob-page-loading')overlay=node;}
 closest(selector){
   if(this.kind==='radio' && selector==='.st-key-pagina label')return this;
   if(this.kind==='mobile' && selector.includes('.st-key-pagina_mobile'))return this;
   return null;
 }
 querySelector(){return {checked:this.checked};}
}
globalThis.document={
 head:new Element(),body:new Element(),documentElement:new Element(),
 createElement:()=>new Element(),addEventListener:(name,fn)=>{listener=fn;},
 querySelector:()=>({getAttribute:()=>state})
};
globalThis.MutationObserver=class {constructor(fn){mutation=fn;}observe(){}};
globalThis.requestAnimationFrame=(fn)=>fn();
globalThis.setTimeout=(fn)=>{timeoutHandler=fn;return 1;};
globalThis.clearTimeout=()=>{};
function click(kind,checked=false,ctrl=false){
 const target=new Element(kind);target.checked=checked;
 listener({target,ctrlKey:ctrl});
}
function visible(){return overlay.dataset.visible==='true';}
'''


@unittest.skipIf(quickjs is None,'Instale quickjs para testar o comportamento JavaScript')
class NavigationFeedbackTests(unittest.TestCase):
    def setUp(self):
        self.context=quickjs.Context()
        self.context.eval(DOM)
        self.context.eval(NAVIGATION_JS.replace('export default function()', 'function renderFeedback()'))
        self.context.eval('renderFeedback()')

    def test_navigation_shows_overlay_until_page_finishes(self):
        self.context.eval("click('radio')")
        self.assertTrue(self.context.eval('visible()'))
        self.context.eval("state='running';mutation();state='notRunning';mutation()")
        self.assertFalse(self.context.eval('visible()'))

    def test_render_of_destination_removes_loading(self):
        self.context.eval("click('mobile');renderFeedback()")
        self.assertFalse(self.context.eval('visible()'))

    def test_selected_page_and_modified_click_do_not_block(self):
        self.context.eval("click('radio',true)")
        self.assertFalse(self.context.eval('visible()'))
        self.context.eval("click('mobile',false,true)")
        self.assertFalse(self.context.eval('visible()'))

    def test_timeout_releases_page_on_failed_navigation(self):
        self.context.eval("click('mobile');timeoutHandler()")
        self.assertFalse(self.context.eval('visible()'))

    def test_unrelated_widgets_do_not_trigger_loading(self):
        self.context.eval("click('filter')")
        self.assertFalse(self.context.eval('visible()'))
