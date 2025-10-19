import 'package:flutter/material.dart';

class ManageCredentialsTab extends StatelessWidget {
  const ManageCredentialsTab({super.key, this.label = '管理憑證'});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Text(
        label,
        style: const TextStyle(
          fontSize: 24,
          fontWeight: FontWeight.w600,
          color: Colors.black,
        ),
      ),
    );
  }
}
