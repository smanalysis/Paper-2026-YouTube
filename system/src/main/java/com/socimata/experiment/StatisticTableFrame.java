package com.socimata.experiment;

import javax.swing.*;
import javax.swing.table.AbstractTableModel;
import javax.swing.table.DefaultTableCellRenderer;
import java.awt.*;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.List;

public class StatisticTableFrame extends JFrame {

    public StatisticTableFrame(List<TableData> dataList) {
        setTitle("实验进度情况");
        setDefaultCloseOperation(JFrame.DISPOSE_ON_CLOSE);
        setSize(1000, 500);
        setLocationRelativeTo(null);

        // Create table model
        TableModel model = new TableModel(dataList);
        JTable table = new JTable(model);

        // Set column renderers
        table.getColumn("Status").setCellRenderer(new StatusRenderer());
        table.getColumn("Progress").setCellRenderer(new ProgressBarRenderer());

        // Improve table appearance
        table.setRowHeight(30);
        table.setIntercellSpacing(new Dimension(5, 5));
        table.setShowGrid(false);

        // Add table to scroll pane
        JScrollPane scrollPane = new JScrollPane(table);
        add(scrollPane, BorderLayout.CENTER);

        // Add a refresh button for demonstration
        JButton refreshButton = new JButton("切换");
        refreshButton.addActionListener(e -> {
            MainWin.toggle(dataList.get(table.getSelectedRow()).name);
        });

        JPanel buttonPanel = new JPanel(new FlowLayout(FlowLayout.RIGHT));
        buttonPanel.add(refreshButton);
        add(buttonPanel, BorderLayout.SOUTH);
    }

    /*
    public static void main(String[] args) {
        // Create sample data
        List<TableData> dataList = new ArrayList<>();
        dataList.add(new TableData("Service A", "Running", 2, new Date(), 75));
        dataList.add(new TableData("Service B", "Stopped", 5, new Date(System.currentTimeMillis() - 3600000), 30));
        dataList.add(new TableData("Service C", "Running", 0, new Date(System.currentTimeMillis() - 86400000), 90));
        dataList.add(new TableData("Service D", "Maintenance", 1, new Date(), 50));

        SwingUtilities.invokeLater(() -> {
            new StatisticTableFrame(dataList).setVisible(true);
        });
    }*/

    // Data model class
    public static class TableData {
        public String name;
        public String status;
        public int exceptionNum;
        public Date lastActiveTime;
        public int progress;

        public TableData(String name, String status, int exceptionNum, Date lastActiveTime, int progress) {
            this.name = name;
            this.status = status;
            this.exceptionNum = exceptionNum;
            this.lastActiveTime = lastActiveTime;
            this.progress = progress;
        }
    }

    // Table model class
    static class TableModel extends AbstractTableModel {
        private final List<TableData> dataList;
        private final String[] columnNames = {"Name", "Status", "Exceptions", "Last Active", "Progress"};

        public TableModel(List<TableData> dataList) {
            this.dataList = dataList;
        }

        @Override
        public int getRowCount() {
            return dataList.size();
        }

        @Override
        public int getColumnCount() {
            return columnNames.length;
        }

        @Override
        public String getColumnName(int column) {
            return columnNames[column];
        }

        @Override
        public Class<?> getColumnClass(int columnIndex) {
            if (columnIndex == 4) return Integer.class; // Progress column
            return super.getColumnClass(columnIndex);
        }

        @Override
        public Object getValueAt(int rowIndex, int columnIndex) {
            TableData data = dataList.get(rowIndex);
            return switch (columnIndex) {
                case 0 -> data.name;
                case 1 -> data.status;
                case 2 -> data.exceptionNum;
                case 3 -> new SimpleDateFormat("yyyy-MM-dd HH:mm").format(data.lastActiveTime);
                case 4 -> data.progress;
                default -> null;
            };
        }

        @Override
        public boolean isCellEditable(int row, int column) {
            return column == 5; // Only the Action column is editable
        }
    }

    // Custom renderer for status column
    static class StatusRenderer extends DefaultTableCellRenderer {
        @Override
        public Component getTableCellRendererComponent(JTable table, Object value, boolean isSelected, boolean hasFocus, int row, int column) {
            Component c = super.getTableCellRendererComponent(table, value, isSelected, hasFocus, row, column);
            if (value != null) {
                String status = value.toString();
                switch (status) {
                    case "Running" -> {
                        c.setBackground(new Color(200, 255, 200)); // Light green
                        c.setForeground(Color.BLACK);
                    }
                    case "Stopped" -> {
                        c.setBackground(new Color(255, 200, 200)); // Light red
                        c.setForeground(Color.BLACK);
                    }
                    case "Waiting" -> {
                        c.setBackground(new Color(255, 255, 150)); // Light red
                        c.setForeground(Color.BLACK);
                    }
                    case null, default -> {
                        c.setBackground(table.getBackground());
                        c.setForeground(table.getForeground());
                    }
                }
            }
            return c;
        }
    }

    // Progress bar renderer
    static class ProgressBarRenderer extends DefaultTableCellRenderer {
        private final JProgressBar progressBar = new JProgressBar(0, 100);

        public ProgressBarRenderer() {
            progressBar.setStringPainted(true);
            progressBar.setBorderPainted(false);
        }

        @Override
        public Component getTableCellRendererComponent(JTable table, Object value, boolean isSelected, boolean hasFocus, int row, int column) {
            Integer progress = (Integer) value;
            progressBar.setValue(progress);

            // Change color based on progress
            if (progress > 75) {
                progressBar.setForeground(new Color(0, 180, 0)); // Green
            } else if (progress > 50) {
                progressBar.setForeground(new Color(255, 165, 0)); // Orange
            } else {
                progressBar.setForeground(new Color(220, 0, 0)); // Red
            }

            return progressBar;
        }
    }
}
