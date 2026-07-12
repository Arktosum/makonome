// lib/theme.dart — Mako's look: deep green-black, terminal-green accent.
import 'package:flutter/material.dart';

class MakoColors {
  static const bg = Color(0xFF0A0F0C); // near-black with a green cast
  static const surface = Color(0xFF121A15); // cards, mako bubbles
  static const surfaceLight = Color(0xFF1B2620); // input field
  static const accent = Color(0xFF00E68A); // mako green
  static const text = Color(0xFFE6F2EA);
  static const textDim = Color(0xFF7A9284);
  static const userBubble = Color(0xFF0E3B26);
  static const warn = Color(0xFFF5B942);
  static const err = Color(0xFFEF6363);
}

final makoTheme = ThemeData(
  brightness: Brightness.dark,
  scaffoldBackgroundColor: MakoColors.bg,
  colorScheme: const ColorScheme.dark(
    primary: MakoColors.accent,
    surface: MakoColors.surface,
    onPrimary: Colors.black,
    onSurface: MakoColors.text,
  ),
  appBarTheme: const AppBarTheme(
    backgroundColor: MakoColors.bg,
    elevation: 0,
    centerTitle: false,
  ),
  snackBarTheme: const SnackBarThemeData(
    backgroundColor: MakoColors.surfaceLight,
    contentTextStyle: TextStyle(color: MakoColors.text),
  ),
  fontFamily: 'Roboto',
);
