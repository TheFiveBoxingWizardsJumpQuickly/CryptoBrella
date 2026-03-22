<?php
/**
 * @license    GPL 2 (http://www.gnu.org/licenses/gpl.html)
 * @author     Robert Nitsch <r.s.nitsch@gmail.com>
 *
 * Based on the first socialshareprivacy plugin by Frank Schiebel.
 */

if (!defined('DOKU_INC')) die();
require_once DOKU_PLUGIN.'syntax.php';

class syntax_plugin_socialshareprivacy2 extends DokuWiki_Syntax_Plugin {
    public function getType() {
        return 'substition';
    }

    public function getPType() {
        return 'block';
    }

    public function getSort() {
        return 222;
    }

    public function connectTo($mode) {
        $this->Lexer->addSpecialPattern('\{\{socialshareprivacy2\}\}', $mode, 'plugin_socialshareprivacy2');
        $this->Lexer->addSpecialPattern('\{\{socialshareprivacy2>.+?\}\}', $mode, 'plugin_socialshareprivacy2');
    }

    public function handle($match, $state, $pos, &$handler){
        $match = substr($match, 2, -2);
        $pos = strrpos($match, ">");
        if ( $pos === false ) {
            $type = "socialshareprivacy2";
            $params = array();
            return array($type, $params);
        } else {
            list($type, $options) = split('>', $match, 2);
        }

        $options = split('&', $options);

        foreach($options as $option) {
            list($name, $value) = split('=', $option);
            $params[trim($name)] = trim($value);
        }

        return array($type, $params);
    }

    public function render($mode, &$renderer, $data) {
        if($mode != 'xhtml') return false;

        $renderer->doc .= '<div class="socialshareprivacy"></div>'. DOKU_LF;
        return true;
    }
}
