<?php
/**
 * @license    GPL 2 (http://www.gnu.org/licenses/gpl.html)
 * @author     Robert Nitsch <r.s.nitsch@gmail.com>
 *
 * Based on the first socialshareprivacy plugin by Frank Schiebel.
 */

if (!defined('DOKU_INC')) die();
require_once(DOKU_PLUGIN.'action.php');

class action_plugin_socialshareprivacy2 extends DokuWiki_Action_Plugin {

    public function register(Doku_Event_Handler &$controller) {
       $controller->register_hook('TPL_METAHEADER_OUTPUT', 'BEFORE', $this, 'handle_tpl_metaheader_output');
    }

    public function handle_tpl_metaheader_output(Doku_Event &$event, $param) {
        global $conf, $ID;

        $options = array(
            "buffer_status",
            "delicious_status",
            "disqus_status",
            "facebook_status",
            "flattr_status",
            "gplus_status",
            "hackernews_status",
            "linkedin_status",
            "mail_status",
            "pinterest_status",
            "reddit_status",
            "stumbleupon_status",
            "tumblr_status",
            "twitter_status",
            "xing_status",

            "buffer_order",
            "delicious_order",
            "disqus_order",
            "facebook_order",
            "flattr_order",
            "gplus_order",
            "hackernews_order",
            "linkedin_order",
            "mail_order",
            "pinterest_order",
            "reddit_order",
            "stumbleupon_order",
            "tumblr_order",
            "twitter_order",
            "xing_order"
        );

        foreach ($options as $opt) {
            $opt_value=$this->getConf("$opt");
            $parts = explode("_", $opt, 2);
            if ($parts[1] == "status" && $opt_value == "1") { $opt_value = "on"; }
            if ($parts[1] == "status" && $opt_value == "0") { $opt_value = "off"; }
            if ($parts[1] == "perma_option" && $opt_value == "1") { $opt_value = "on"; }
            if ($parts[1] == "perma_option" && $opt_value == "0") { $opt_value = "off"; }
            if ($opt_value != "") {
                $jsopt["$parts[0]"] .= "'" . $parts[1] . "' : " . "'" .$opt_value . "',";
            }
        }

        $path_prefix = DOKU_BASE."lib/plugins/socialshareprivacy2/SSP/";

        // Output
        $event->data["script"][] = array (
            "type" => "text/javascript",
            "_data" => "",
            "src" => $path_prefix."scripts/jquery.socialshareprivacy.js"
        );
        $event->data["script"][] = array (
            "type" => "text/javascript",
            "_data" => "",
            "src" => $path_prefix."../JC/jquery.cookie.js"
        );

        $services = array();
        $orders = array();

        foreach ($options as $opt) {
            list($service, $setting) = explode("_", $opt, 2);
            $value = $this->getConf($opt);

            if ($setting == "status" && $value == "1") {
                $event->data["script"][] = array (
                    "type" => "text/javascript",
                    "_data" => "",
                    "src" => $path_prefix."scripts/jquery.socialshareprivacy.$service.js"
                );
            } else if ($setting == "order") {
                $services[] = "'$service'";
                $orders[] = $value;
            }
        }

        // Sort services by order and name.
        array_multisort($orders, SORT_ASC, $services, SORT_STRING);

        $settings_order = implode($services, ', ');
        $settings_url = wl($ID, '', true, '&');

        // Service specific settings
        $settings_flattr_uid = $this->getConf("flattr_uid");
        $settings_twitter_via = $this->getConf("twitter_via");

        /*
        TODO:
            For some reason, in the below javascript code, $ cannot be used directly. Maybe it is
            overwritten by some other javascript library.

            The closure is a workaround for this problem.
        */
        $script = <<<JS
    (function ($) {
        $(document).ready(function () {
            $.fn.socialSharePrivacy.settings.description = $("div.page > :not(#dw__toc)").text().substr(0, 300);
            $.fn.socialSharePrivacy.settings.order = [{$settings_order}];
            $.fn.socialSharePrivacy.settings.path_prefix = "{$path_prefix}";
            $.fn.socialSharePrivacy.settings.uri = "{$settings_url}";
            if ($.fn.socialSharePrivacy.settings.services.flattr) {
                $.fn.socialSharePrivacy.settings.services.flattr.uid = "$settings_flattr_uid";
            }
            if ($.fn.socialSharePrivacy.settings.services.twitter) {
                $.fn.socialSharePrivacy.settings.services.twitter.via = "$settings_twitter_via";
            }

            $('.socialshareprivacy').socialSharePrivacy();
        });
    }(jQuery));
JS;

        $event->data["script"][] = array (
            "type" => "text/javascript",
            "charset" => "utf-8",
            "_data" => $script
        );
    }
}
