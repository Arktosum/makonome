// lib/widgets/prompt_inspector.dart — tap a Mako reply to see exactly what
// was sent to the model: colored token bar + expandable prompt sections.
// Token counts are word-based estimates (same method as the web dashboard).
import 'package:flutter/material.dart';
import '../theme.dart';

const _sectionColors = {
  'blue': Color(0xFF3B82F6),
  'purple': Color(0xFFA855F7),
  'green': Color(0xFF22C55E),
  'amber': Color(0xFFF59E0B),
  'cyan': Color(0xFF06B6D4),
  'red': Color(0xFFEF4444),
};

int _estimateTokens(String text) {
  final words = text.split(RegExp(r'\s+')).where((w) => w.isNotEmpty).length;
  return (words * 1.3).round().clamp(1, 1 << 30);
}

void showPromptInspector(
    BuildContext context, List<Map<String, dynamic>> sections) {
  final parsed = sections
      .map((s) => (
            label: (s['label'] ?? '?').toString(),
            color: _sectionColors[s['color']] ?? MakoColors.textDim,
            text: (s['text'] ?? '').toString(),
            tokens: _estimateTokens((s['text'] ?? '').toString()),
          ))
      .toList();
  final total = parsed.fold<int>(0, (a, s) => a + s.tokens);

  showModalBottomSheet(
    context: context,
    backgroundColor: MakoColors.surface,
    isScrollControlled: true,
    shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
    builder: (_) => DraggableScrollableSheet(
      expand: false,
      initialChildSize: 0.7,
      maxChildSize: 0.95,
      builder: (context, scroll) => Column(
        children: [
          const SizedBox(height: 10),
          Container(
            width: 36,
            height: 4,
            decoration: BoxDecoration(
                color: MakoColors.textDim.withValues(alpha: 0.4),
                borderRadius: BorderRadius.circular(2)),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(18, 14, 18, 6),
            child: Row(
              children: [
                const Text('PROMPT BREAKDOWN',
                    style: TextStyle(
                        color: MakoColors.accent,
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                        letterSpacing: 1.5)),
                const Spacer(),
                Text('~$total tokens',
                    style: const TextStyle(
                        color: MakoColors.textDim, fontSize: 12)),
              ],
            ),
          ),
          // the rainbow bar
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 18),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(3),
              child: Row(
                children: [
                  for (final s in parsed)
                    Expanded(
                      flex: (s.tokens * 1000 ~/ (total == 0 ? 1 : total)) + 1,
                      child: Container(height: 5, color: s.color),
                    ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 8),
          Expanded(
            child: ListView(
              controller: scroll,
              padding: const EdgeInsets.fromLTRB(14, 4, 14, 20),
              children: [
                for (final s in parsed)
                  Theme(
                    data: Theme.of(context)
                        .copyWith(dividerColor: Colors.transparent),
                    child: ExpansionTile(
                      tilePadding:
                          const EdgeInsets.symmetric(horizontal: 8),
                      childrenPadding:
                          const EdgeInsets.fromLTRB(12, 0, 12, 12),
                      leading: Container(
                          width: 10,
                          height: 10,
                          decoration: BoxDecoration(
                              color: s.color, shape: BoxShape.circle)),
                      title: Text(s.label,
                          style: TextStyle(
                              color: s.color,
                              fontSize: 13,
                              fontWeight: FontWeight.w600)),
                      trailing: Text(
                          '${s.tokens} tok · ${total == 0 ? 0 : (s.tokens * 100 / total).toStringAsFixed(1)}%',
                          style: const TextStyle(
                              color: MakoColors.textDim, fontSize: 11)),
                      children: [
                        Align(
                          alignment: Alignment.centerLeft,
                          child: SelectableText(
                            s.text,
                            style: const TextStyle(
                                color: MakoColors.text,
                                fontSize: 12,
                                height: 1.4,
                                fontFamily: 'monospace'),
                          ),
                        ),
                      ],
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    ),
  );
}
