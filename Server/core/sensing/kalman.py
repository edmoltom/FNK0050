class KalmanFilter:
    """
    @brief Implements a simple 1D Kalman filter for smoothing sensor readings.
    @details
    This implementation is tailored for smoothing ADC readings with a 
    conditional smoothing strategy when sudden large changes occur.
    """

    def __init__(self, process_noise, measurement_noise, jump_threshold=60, blend_factor=0.4):
        """
        @brief Constructor for KalmanFilter.
        @param process_noise Process noise covariance (Q).
        @param measurement_noise Measurement noise covariance (R).
        @param jump_threshold Threshold for detecting large measurement jumps.
        @param blend_factor Weight for new value in case of large jumps (0-1).
        """
        self.Q = process_noise
        self.R = measurement_noise
        self.jump_threshold = jump_threshold
        self.blend_factor = blend_factor

        self.P_predicted = 1.0    # Predicted covariance estimate
        self.Kg = 0.0             # Kalman gain
        self.P_updated = 1.0      # Updated covariance estimate
        self.x_predicted = 0.0    # Predicted state estimate
        self.Z_k = 0.0            # Current measurement
        self.prev_filtered = 0.0  # Previous filtered value

    def update_kalman(self, measurement):
        """
        @brief Applies the Kalman filter to the provided measurement.
        @param measurement Raw sensor value (e.g., ADC).
        @return Filtered value.
        """
        self.Z_k = measurement

        # Special handling for sudden large jumps
        if abs(self.prev_filtered - measurement) >= self.jump_threshold:
            self.x_updated = (measurement * self.blend_factor +
                              self.prev_filtered * (1 - self.blend_factor))
        else:
            self.x_updated = self.prev_filtered

        # Prediction step
        self.x_predicted = self.x_updated
        self.P_predicted = self.P_updated + self.Q

        # Kalman gain
        self.Kg = self.P_predicted / (self.P_predicted + self.R)

        # Update step
        filtered_value = self.x_predicted + self.Kg * (self.Z_k - self.x_predicted)
        self.P_updated = (1 - self.Kg) * self.P_predicted

        # Store results for next iteration
        self.P_predicted = self.P_updated
        self.prev_filtered = filtered_value

        return filtered_value
