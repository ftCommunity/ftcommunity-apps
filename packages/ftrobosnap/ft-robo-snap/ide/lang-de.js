/*
 * lang-de.js: German translation for FT-Robo-Snap
 *
 * This file contains only translations for FT-Robo-Snap specific blocks
 * and other elements. Translations for standard IDE elements are loaded from
 * the original Snap! translation file
 *
 * Note to translators: This file has basically the same structure as a
 * "standard" Snap! translation file, and the same rules and restritions for
 * editing apply.
 *
 * (c) 2016 Richard Kunze
 *
 * This file is part of FT-Robo-Snap (https://github.com/rkunze/ft-robo-snap)
 *
 * FT-Robo-Snap is free software licensed under the Affero Gnu Public License,
 * either version 3 or (at your discretion) any later version.
 *
 */

/*global FTRoboSnap*/

FTRoboSnap.dict.de = {

    /**** Block labels. ****/
    "$ftrobo set %ftroboOutput to %ftroboOutputValue":
        "$ftrobo setze %ftroboOutput auf %ftroboOutputValue",

    "$ftrobo set speed of %ftroboMotor to %ftroboMotorValue":
        "$ftrobo Setze Geschwindigkeit von %ftroboMotor auf %ftroboMotorValue",


    "$ftrobo run %ftroboMotorList at speed %ftroboMotorValue %br and stop after %ftroboSteps steps":
        "$ftrobo starte %ftroboMotorList mit Tempo %ftroboMotorValue %br und stoppe nach %ftroboSteps Schritten",

    "$ftrobo is motor %ftroboMotor running?":
        "$ftrobo läuft Motor %ftroboMotor ?",

    "$ftrobo is switch %ftroboInput on?":
        "$ftrobo ist Schalter %ftroboInput an?",

    "$ftrobo current value of %ftroboCounter":
        "$ftrobo Zählerstand von %ftroboCounter",

    "$ftrobo current value of %ftroboInput":
        "$ftrobo Wert von %ftroboInput",

    "$ftrobo has %ftroboWatchAll changed?":
        "$ftrobo hat sich der Wert von %ftroboWatchAll geändert?",

    "$ftrobo turn off all outputs":
        "$ftrobo alles ausschalten",

    "$ftrobo watch %ftroboCounterList for value changes":
        "$ftrobo überwache Änderungen von %ftroboCounterList",

    "$ftrobo watch %ftroboInputList for switch state changes":
        "$ftrobo überwache Schaltvorgänge von %ftroboInputList",

    "$ftrobo stop watching %ftroboInputOrCounterList":
        "$ftrobo stoppe Überwachung von %ftroboInputOrCounterList",

    "$ftrobo set mode to %ftroboMode":
        "$ftrobo wechsle in Modus %ftroboMode",

    "$ftrobo enable output %ftroboMotorOrOutputList":
        "$ftrobo Aktiviere %ftroboMotorOrOutputList",


    /**** Menu items for input slot dropdowns  ****/
    // %ftroboOutputValue (single output range hints)
    "0 (off)": "0 (aus)",
    "512 (max)": "512 (maximal)",

    // %ftroboMotorValue (motor output range hints)
    "+512 (forward)" : "+512 (vorwärts)",
    "0 (stop)": "0 (stop)",
    "-512 (back)" : "-512 (rückwärts)",

};


// Translators: Do not edit anything below this line
// ===========================================================================
// Load the original translation file and monkey patch our additions
// into the global dictionary
FTRoboSnap.monkeyPatchTranslation(document.getElementById("language"));
