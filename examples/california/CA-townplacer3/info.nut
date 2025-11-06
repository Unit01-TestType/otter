/*
 * 
*/

require("version.nut");

class FMainClass extends GSInfo {
	function GetAuthor()		{ return "Unit01-TestType"; }
	function GetName()			{ return "CA-townplacer3"; }
	function GetDescription() 	{ return "A gamescript for a real-world West Coast scenario"; }
	function GetVersion()		{ return SELF_VERSION; }
	function GetDate()			{ return "2024-12-16"; }
	function CreateInstance()	{ return "MainClass"; }
	function GetShortName() 	{ return "CATP"; }
	function GetAPIVersion() 	{ return "1.11"; }
	function GetURL() 			{ return ""; }

	function GetSettings() {
		AddSetting({name = "log_level", description = "Debug: Log level (higher = print more)", easy_value = 3, medium_value = 3, hard_value = 3, custom_value = 3, flags = CONFIG_INGAME, min_value = 1, max_value = 3});
		AddLabels("log_level", {_1 = "1: Info", _2 = "2: Verbose", _3 = "3: Debug" } );
	}
}

RegisterGS(FMainClass());
