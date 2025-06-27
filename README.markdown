# Kitchenware-AI

## Process Flow
The following flowchart illustrates the technical workflow of the Kitchenware-AI system, detailing the interaction between hardware, software, and external services for food recognition, weight measurement, nutritional analysis, and inventory management.

```mermaid
graph TD
    A[Start: Kitchenware-AI System] --> B[Raspberry Pi Camera: Capture Food Image]
    B -->|Image Data| C[RecognitionModel: LLM-based Food Detection]
    C -->|Detected Food Item| D[Nutritionix API: Retrieve Nutritional Data]
    C -->|Food Metadata| E[InventoryManager: Log Item]
    B -->|Image File| F[Amazon S3: Store Image]
    G[Raspberry Pi Weight Sensor: Measure Food Weight] -->|Weight Data| E
    D -->|Nutritional Data| E
    E --> H[KitchenwareItem: Update Inventory Record]
    H --> I[Output: Display/Log Nutritional & Inventory Data]
    F -->|Image URL| H
    I --> J[End: Data Accessible for User]
    
    subgraph Hardware Layer
        B
        G
    end
    subgraph Software Layer
        C
        E
        H
        I
    end
    subgraph External Services
        D
        F
    end
```

*Note*: To visualize the flowchart, view this README on GitHub or paste the Mermaid code into the [Mermaid Live Editor](https://mermaid-js.github.io/mermaid-live-editor/) to export as an SVG or PNG.

## Overview
Kitchenware-AI is an innovative AI-powered kitchen management system designed to streamline food tracking, inventory management, and nutritional analysis. By integrating hardware components like a Raspberry Pi and camera with advanced AI algorithms and cloud services, this project automates food identification, weight measurement, and nutritional logging. The system leverages machine learning, image processing, and APIs (such as Nutritionix) to provide real-time insights into daily food consumption, making it a powerful tool for health-conscious individuals and kitchen enthusiasts.

## Features
- **Food Recognition**: Automatically identifies food items using a camera and a large language model (LLM) for accurate detection.
- **Weight Monitoring**: Tracks food weight in real-time using sensors connected to a Raspberry Pi.
- **Nutritional Analysis**: Integrates with the Nutritionix API to retrieve detailed nutritional information for identified food items.
- **Inventory Management**: Manages kitchenware and food inventory through a dedicated `InventoryManager` module.
- **Image Processing**: Captures and processes food images, with hand detection to improve accuracy, and stores them in Amazon S3 for cloud-based access.
- **Data Logging**: Logs nutritional data and inventory details for easy tracking and analysis.

## Technical Architecture
The system combines hardware and software components to deliver a seamless kitchen management experience:

### Hardware
- **Raspberry Pi**: Powers the system, interfacing with sensors and cameras for data collection.
- **Camera Module**: Captures high-quality images of food items for recognition.
- **Weight Sensors**: Measures food weight in real-time for precise tracking.

### Software
- **Machine Learning Libraries**: Utilizes AI models for food recognition and hand detection.
- **Image Processing Libraries**: Processes images for accurate identification and analysis.
- **Data Handling Libraries**: Manages datasets for inventory and nutritional logging.
- **Cloud Integration**: Stores images and data in Amazon S3 for scalability and accessibility.
- **Nutritionix API**: Retrieves nutritional information for identified food items.
- **Core Modules**:
  - `KitchenwareItem`: Manages individual kitchen items.
  - `InventoryManager`: Tracks collections of kitchenware and food items.
  - `RecognitionModel`: Handles image-based food identification using an LLM.

## Installation
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/yourusername/kitchenware-ai.git
   cd kitchenware-ai
   ```

2. **Set Up Hardware**:
   - Connect the Raspberry Pi to the camera module and weight sensors as per the hardware documentation.
   - Ensure the Raspberry Pi is configured with the latest version of Raspberry Pi OS.

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   Required Python libraries include those for machine learning (e.g., TensorFlow or PyTorch), image processing (e.g., OpenCV), and API communication (e.g., requests).

4. **Configure APIs and Cloud Services**:
   - Obtain an API key from [Nutritionix](https://www.nutritionix.com/business/api) and add it to a `.env` file:
     ```
     NUTRITIONIX_API_KEY=your_api_key
     ```
   - Set up an Amazon S3 bucket and configure credentials in the `.env` file:
     ```
     AWS_ACCESS_KEY_ID=your_access_key
     AWS_SECRET_ACCESS_KEY=your_secret_key
     AWS_S3_BUCKET=your_bucket_name
     ```

5. **Run the Application**:
   ```bash
   python main.py
   ```
   This starts the kitchen management system, initializing the camera, sensors, and AI models.

## Usage
1. **Food Detection**:
   - Place food items in front of the camera.
   - The system automatically captures images, detects food using the LLM, and sends the data to the Nutritionix API for nutritional analysis.

2. **Inventory Tracking**:
   - Use the `InventoryManager` to add or update kitchenware and food items.
   - View the current inventory through the command-line interface or a web dashboard (if implemented).

3. **Nutritional Logging**:
   - Nutritional data is logged automatically and can be accessed via the system's output or cloud storage.

4. **Weight Monitoring**:
   - Real-time weight measurements are displayed and logged for each food item.

## Example
```python
from kitchenware_ai import KitchenwareItem, InventoryManager, RecognitionModel

# Initialize inventory and recognition model
inventory = InventoryManager()
recognition_model = RecognitionModel()

# Capture and identify food
image = capture_image()  # Captures image using Raspberry Pi camera
food_item = recognition_model.identify_food(image)

# Get nutritional data
nutritional_info = inventory.log_nutritional_data(food_item)

# Add to inventory
item = KitchenwareItem(name=food_item, weight=measure_weight())
inventory.add_item(item)
```

## Future Enhancements
- Add a web-based or mobile app interface for easier user interaction.
- Implement real-time recipe suggestions based on identified ingredients.
- Enhance hand detection for more precise food recognition in busy kitchen environments.
- Integrate with smart home systems for automated inventory reordering.

## Contributing
Contributions are welcome! Please follow these steps:
1. Fork the repository.
2. Create a new branch (`git checkout -b feature/your-feature`).
3. Commit your changes (`git commit -m 'Add your feature'`).
4. Push to the branch (`git push origin feature/your-feature`).
5. Open a pull request.

## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contact
For questions or feedback, please open an issue on GitHub or contact [your email or preferred contact method].