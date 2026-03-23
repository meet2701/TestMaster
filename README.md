# DASS Assignment 2

**Student:** Meet Parekh
**Roll Number:** 2024101122

---

## Repository Links

- **GitHub Repository:** `https://github.com/meet2701/TestMaster`
- **OneDrive (complete assignment with .git):** `https://iiithydstudents-my.sharepoint.com/:f:/g/personal/meet_parekh_students_iiit_ac_in/IgAlhEY6ZeFzTbWrxOxoeuwKAan-Dw4-2OvDwg3h1eazi8M?e=3vnI8m`

---

## Folder Structure

```
2024101122/
├── whitebox/
│   ├── moneypoly/        # source code
│   ├── diagrams/
│   ├── tests/
│   └── report.pdf
├── integration/
│   ├── code/             # source code
│   ├── diagrams/
│   ├── tests/
│   └── report.pdf
├── blackbox/
│   ├── tests/
│   └── report.pdf
└── README.md
```

---

## How to Run the Code

### Whitebox

```bash
cd whitebox/moneypoly
python3 main.py
```

### Integration

```bash
cd integration/code
python3 main.py
```

---

## How to Run the Tests

### Whitebox Tests

```bash
cd whitebox
pytest tests/test_whitebox.py -v
```

### Integration Tests

```bash
cd integration
pytest tests/test_integration.py -v
```

### Blackbox Tests

```bash
cd blackbox
pytest tests/test_blackbox.py -v
```