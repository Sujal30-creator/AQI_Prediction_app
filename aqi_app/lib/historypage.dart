import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

class HistoryPage extends StatefulWidget {
  final String loggedInUser; // ✅ Accept username from PredictionPage

  const HistoryPage({super.key, required this.loggedInUser});

  @override
  // ignore: library_private_types_in_public_api
  _HistoryPageState createState() => _HistoryPageState();
}

class _HistoryPageState extends State<HistoryPage> {
  List<dynamic> _history = [];

  Future<void> fetchHistory() async {
    const String apiUrl = 'http://10.0.2.2:5000/history';
    final response = await http.post(
      Uri.parse(apiUrl),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({'username': widget.loggedInUser}), // ✅ Send correct username
    );

    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      setState(() {
        _history = data['history'];
      });
    } else {
      setState(() {
        _history = [];
      });
    }
  }

  @override
  void initState() {
    super.initState();
    fetchHistory();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('AQI History')),
      body: ListView.builder(
        itemCount: _history.length,
        itemBuilder: (context, index) {
          final record = _history[index];
          return ListTile(
            title: Text('Month ${record['month_index']}: AQI ${record['aqi_value']}'),
            subtitle: Text('Timestamp: ${record['timestamp']}'),
          );
        },
      ),
    );
  }
}
