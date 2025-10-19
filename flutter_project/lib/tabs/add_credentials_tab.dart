import 'package:flutter/material.dart';

class AddCredentialsTab extends StatelessWidget {
  const AddCredentialsTab({super.key, this.label = '加入憑證'});

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
