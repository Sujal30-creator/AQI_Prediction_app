import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'historypage.dart';

class PredictionPage extends StatefulWidget {
  final String loggedInUser;

  const PredictionPage({super.key, required this.loggedInUser});

  @override
  _PredictionPageState createState() => _PredictionPageState();
}

class _PredictionPageState extends State<PredictionPage> {
  final TextEditingController _monthController = TextEditingController();
  String? _aqiResult;
  String? _feedback;
  bool _isSignedUp = false;
  bool _isNotebookRunning = false;
  String? _notebookResult;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _checkUserRegistration();
  }

  Future<void> _checkUserRegistration() async {
    try {
      const String apiUrl = 'http://10.0.2.2:5000/check-user';
      final response = await http.post(
        Uri.parse(apiUrl),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'username': widget.loggedInUser}),
      );

      setState(() {
        _isSignedUp = response.statusCode == 200;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _isSignedUp = false;
        _isLoading = false;
      });
    }
  }

  Future<void> fetchAQI() async {
    if (!_isSignedUp) {
      _showSignUpDialog();
      return;
    }

    final int? monthIndex = int.tryParse(_monthController.text);
    if (monthIndex == null || monthIndex < 1 || monthIndex > 12) {
      setState(() {
        _aqiResult = "❌ Invalid month! Please enter a value between 1 and 12.";
      });
      return;
    }

    setState(() {
      _aqiResult = null;
      _feedback = null;
    });

    try {
      const String apiUrl = 'http://10.0.2.2:5000/predict';
      final response = await http.post(
        Uri.parse('$apiUrl/$monthIndex'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'username': widget.loggedInUser}),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        setState(() {
          _aqiResult = "AQI for Month $monthIndex: ${data['aqi_value']}";
          _feedback = data['solution'];
        });
      } else if (response.statusCode == 401) {
        setState(() {
          _isSignedUp = false;
          _aqiResult = "❌ Session expired. Please login again.";
        });
        _showSignUpDialog();
      } else {
        setState(() {
          _aqiResult = "❌ Server Error: ${response.statusCode}";
        });
      }
    } catch (e) {
      setState(() {
        _aqiResult = "❌ Connection error: $e";
      });
    }
  }

  Future<void> runNotebook() async {
    if (!_isSignedUp) {
      _showSignUpDialog();
      return;
    }

    // Get month from controller and validate
    final month = int.tryParse(_monthController.text);
    if (month == null || month < 1 || month > 12) {
      setState(() {
        _notebookResult = "❌ Please enter a valid month (1-12)";
      });
      return;
    }

    setState(() {
      _isNotebookRunning = true;
      _notebookResult = null;
    });

    try {
      const String notebookUrl = 'http://10.0.2.2:5000/run-notebook';
      final response = await http.post(
        Uri.parse(notebookUrl),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'username': widget.loggedInUser,
          'month': month,  // Added month parameter
        }),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        setState(() {
          _notebookResult = data['message'] ?? "Notebook executed successfully";
          // You might want to handle visualizations here if returned
          if (data['visualizations'] != null) {
            // Process visualizations data
          }
        });
      } else if (response.statusCode == 400) {
        final errorData = jsonDecode(response.body);
        setState(() {
          _notebookResult = "❌ ${errorData['error']}";
        });
      } else if (response.statusCode == 401) {
        setState(() {
          _isSignedUp = false;
          _notebookResult = "❌ Session expired. Please login again.";
        });
        _showSignUpDialog();
      } else {
        setState(() {
          _notebookResult = "Error: ${response.statusCode} - ${response.body}";
        });
      }
    } catch (e) {
      setState(() {
        _notebookResult = "Connection error: $e";
      });
    } finally {
      setState(() {
        _isNotebookRunning = false;
      });
    }
  }

  void _showSignUpDialog() {
    showDialog(
      context: context,
      builder: (context) =>
          AlertDialog(
            title: const Text("Registration Required"),
            content: const Text("You need to register to use this feature"),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text("Cancel"),
              ),
              TextButton(
                onPressed: () {
                  Navigator.pop(context);
                  Navigator.pushNamed(context, '/signup');
                },
                child: const Text("Sign Up"),
              ),
            ],
          ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        title: const Text(
            'AQI Prediction', style: TextStyle(fontWeight: FontWeight.bold)),
        centerTitle: true,
        backgroundColor: Colors.transparent,
        elevation: 0,
      ),
      body: Stack(
        children: [
          // Background Gradient
          Container(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [Colors.blue.shade900, Colors.purple.shade900],
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
              ),
            ),
          ),

          // Loading Indicator
          if (_isLoading)
            const Center(child: CircularProgressIndicator()),

          // Main Content
          if (!_isLoading)
            Center(
              child: SingleChildScrollView(
                child: Container(
                  margin: const EdgeInsets.symmetric(horizontal: 20),
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.2),
                    borderRadius: BorderRadius.circular(20),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withOpacity(0.2),
                        blurRadius: 10,
                        spreadRadius: 3,
                      ),
                    ],
                  ),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      // Welcome Message
                      Text(
                        'Welcome, ${widget.loggedInUser}!',
                        style: const TextStyle(
                          fontSize: 20,
                          color: Colors.white,
                        ),
                      ),
                      const SizedBox(height: 10),

                      // AQI Title
                      const Text(
                        'AQI Prediction',
                        style: TextStyle(
                          fontSize: 28,
                          fontWeight: FontWeight.bold,
                          color: Colors.white,
                        ),
                      ),
                      const SizedBox(height: 20),

                      // Month Input Field
                      TextField(
                        controller: _monthController,
                        keyboardType: TextInputType.number,
                        style: const TextStyle(color: Colors.white),
                        decoration: InputDecoration(
                          hintText: 'Enter Month (1-12)',
                          hintStyle: const TextStyle(color: Colors.white70),
                          filled: true,
                          fillColor: Colors.white.withOpacity(0.2),
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(15),
                            borderSide: BorderSide.none,
                          ),
                        ),
                      ),
                      const SizedBox(height: 20),

                      // AQI Data Button
                      ElevatedButton(
                        onPressed: fetchAQI,
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color.fromARGB(
                              255, 5, 140, 43),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(15),
                          ),
                          padding: const EdgeInsets.symmetric(
                              vertical: 12, horizontal: 20),
                        ),
                        child: const Text(
                          'Get AQI Data',
                          style: TextStyle(fontSize: 18, fontWeight: FontWeight
                              .bold),
                        ),
                      ),
                      const SizedBox(height: 20),

                      // Visualization Button
                      ElevatedButton(
                        onPressed: _isNotebookRunning ? null : runNotebook,
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.deepPurple,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(15),
                          ),
                          padding: const EdgeInsets.symmetric(
                              vertical: 12, horizontal: 20),
                        ),
                        child: _isNotebookRunning
                            ? const CircularProgressIndicator(
                            color: Colors.white)
                            : const Text(
                          'Get Visualization',
                          style: TextStyle(fontSize: 18, fontWeight: FontWeight
                              .bold),
                        ),
                      ),
                      const SizedBox(height: 20),

                      // Notebook Execution Result
                      if (_notebookResult != null)
                        Padding(
                          padding: const EdgeInsets.only(top: 10),
                          child: Text(
                            _notebookResult!,
                            style: const TextStyle(color: Colors.white,
                                fontSize: 16),
                            textAlign: TextAlign.center,
                          ),
                        ),

                      // Display AQI Result
                      if (_aqiResult != null)
                        Padding(
                          padding: const EdgeInsets.only(top: 10),
                          child: Text(
                            _aqiResult!,
                            style: const TextStyle(color: Colors.white,
                                fontSize: 18),
                            textAlign: TextAlign.center,
                          ),
                        ),

                      // Display Feedback
                      if (_feedback != null)
                        Padding(
                          padding: const EdgeInsets.only(top: 10),
                          child: Text(
                            _feedback!,
                            style: const TextStyle(color: Colors.white,
                                fontSize: 16),
                            textAlign: TextAlign.center,
                          ),
                        ),

                      const SizedBox(height: 20),

                      // History Button
                      ElevatedButton(
                        onPressed: () {
                          Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (context) =>
                                  HistoryPage(
                                      loggedInUser: widget.loggedInUser),
                            ),
                          );
                        },
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.orangeAccent,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(15),
                          ),
                          padding: const EdgeInsets.symmetric(
                              vertical: 12, horizontal: 20),
                        ),
                        child: const Text(
                          'View History',
                          style: TextStyle(fontSize: 18, fontWeight: FontWeight
                              .bold),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}