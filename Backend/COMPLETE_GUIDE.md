# 📚 FeedVox AI - Complete Procedures & Advanced Guide

**The definitive guide for using FeedVox AI from basic setup to advanced medical workflow integration.**

---

## 🎯 **QUICK START (3 STEPS)**

### **Step 1: Start the System**
```bash
cd feedvox.ai
venv\Scripts\activate  # Windows
python main.py
```

### **Step 2: Upload Audio**
- Open Postman → FeedVox AI Collection
- Select "Upload Audio for Transcription"
- Click **"Select Files"** → Choose your audio file
- Send request

### **Step 3: Extract Medical Note**
- Copy the transcribed `text` from response
- Select "Extract Medical Note from Text"
- Paste text in JSON body → Send request
- **Done!** Complete medical note with 15+ codes

---

## 📤 **DETAILED UPLOAD PROCEDURES**

### **🎵 Supported Audio Formats & Best Practices**

| Format | Quality | Use Case | Notes |
|--------|---------|----------|-------|
| **WAV** | ⭐⭐⭐⭐⭐ | **Recommended** | Best accuracy, no compression |
| **MP3** | ⭐⭐⭐⭐ | General use | Good balance of size/quality |
| **M4A** | ⭐⭐⭐⭐ | Apple devices | High quality, good compression |
| **FLAC** | ⭐⭐⭐⭐⭐ | Archival | Lossless, larger files |
| **OGG** | ⭐⭐⭐ | Open source | Good quality, smaller files |
| **AAC** | ⭐⭐⭐⭐ | Mobile devices | Efficient compression |
| **MP4** | ⭐⭐⭐ | Video files | Extract audio from video |

### **📏 Audio Requirements**
- **Duration**: No strict limit (tested up to 1 hour)
- **File Size**: < 100MB recommended for upload
- **Quality**: Clear speech, minimal background noise
- **Sample Rate**: 16kHz+ recommended
- **Channels**: Mono or stereo both supported

### **🎤 Recording Best Practices**
- **Distance**: 1-3 feet from microphone
- **Environment**: Quiet room, minimal echo
- **Speaking**: Clear enunciation, normal pace
- **Equipment**: Use dedicated microphone if possible
- **Format**: Record in WAV if you have the choice

---

## 🔧 **STEP-BY-STEP POSTMAN PROCEDURES**

### **📦 Import Collection**
1. Download `FeedVox_AI_Postman_Collection.json`
2. Open Postman
3. Click **Import** button (top left)
4. Drag and drop the JSON file OR click "Choose files"
5. ✅ Collection appears in left sidebar

### **📤 Upload Audio File (FORM-DATA)**
1. **Select Request**: "Upload Audio for Transcription"
2. **Go to Body Tab**: Click "Body" below the URL bar
3. **Ensure form-data**: Should be pre-selected (not raw/binary)
4. **Find audio_file Row**: Key = `audio_file`, Type = File
5. **Click "Select Files"**: Button on the right side
6. **Browse & Select**: Choose your audio file
7. **Optional Language**: Add `language` = `en` for English
8. **Send Request**: Click blue "Send" button
9. **Wait for Processing**: 1-3 minutes depending on file size

**✅ Expected Response:**
```json
{
  "success": true,
  "message": "Audio transcribed successfully",
  "transcription_id": "uuid-here",
  "text": "Your complete transcription...",
  "duration_seconds": 195.59,
  "processing_time_seconds": 67.45
}
```

### **📝 Extract Medical Note (RAW JSON)**
1. **Copy Transcription Text**: Select all text from `"text"` field
2. **Select Request**: "Extract Medical Note from Text"
3. **Go to Body Tab**: Click "Body"
4. **Ensure Raw JSON**: Select "raw" → dropdown "JSON"
5. **Replace Placeholder**: Delete placeholder and paste your text
6. **Format JSON**: Ensure proper JSON format:
```json
{
  "transcript_text": "Your transcribed text here..."
}
```
7. **Send Request**: Processing takes 5-15 seconds

**✅ Expected Response:**
```json
{
  "success": true,
  "note_id": "note-uuid",
  "medical_note": {
    "chief_complaint": "Chest pain for past few days",
    "history_present_illness": "Detailed symptoms...",
    "past_medical_history": "Previous conditions...",
    "medications": "Current medications...",
    "allergies": "Known allergies...",
    "social_history": "Lifestyle factors...",
    "family_history": "Family medical history...",
    "vital_signs": "Current vitals...",
    "physical_exam": "Examination findings...",
    "assessment": "Clinical assessment...",
    "plan": "Treatment plan..."
  },
  "medical_codes": {
    "icd_codes": [...],
    "cpt_codes": [...],
    "snomed_codes": [...],
    "total_codes": 15
  }
}
```

### **📋 Get Complete Medical Note (URL PARAMETERS)**
1. **Copy Note ID**: From extraction response
2. **Select Request**: "Get Medical Note with Codes"
3. **Replace URL Parameter**: Change `YOUR_NOTE_ID_HERE` to actual ID
4. **Example URL**: `/api/v1/notes/note-550e8400-e29b-41d4-a716-446655440000`
5. **Send Request**: Retrieves complete record

### **🔍 Search Medical Codes (QUERY PARAMETERS)**
1. **Select Search Request**: ICD/CPT/SNOMED search
2. **Modify Parameters**: In "Params" tab or directly in URL
3. **Common Searches**:
   - `query=chest pain` (symptoms)
   - `query=hypertension` (conditions)
   - `query=office visit` (procedures)
   - `query=follow-up` (follow-up care)
4. **Adjust Limit**: `limit=5` (fewer results) or `limit=20` (more results)

---

## 🏥 **MEDICAL WORKFLOW PROCEDURES**

### **🩺 Complete Medical Documentation Workflow**

#### **Phase 1: Capture**
1. **Record Consultation**: Use clear audio recording
2. **Save in Supported Format**: Prefer WAV for best results
3. **Verify Audio Quality**: Ensure clear speech before uploading

#### **Phase 2: Transcription**
1. **Upload to FeedVox AI**: Via Postman or API
2. **Wait for Processing**: ~1/3 of audio duration
3. **Review Transcription**: Check for accuracy
4. **Manual Corrections**: Edit if needed before note extraction

#### **Phase 3: Medical Note Extraction**
1. **Submit for Processing**: Use transcript text
2. **Review Extracted Fields**: All 11 medical sections
3. **Validate Information**: Ensure clinical accuracy
4. **Note Completion**: 90%+ field completion expected

#### **Phase 4: Medical Coding**
1. **Automatic Code Assignment**: Happens during extraction
2. **Review Assigned Codes**: ICD-10, CPT, SNOMED
3. **Validate Code Relevance**: Check confidence scores (60%+)
4. **Manual Override**: Adjust codes if needed

#### **Phase 5: Documentation**
1. **Export Complete Record**: Full medical note + codes
2. **Integrate with EHR**: Via API or manual entry
3. **Archive Audio**: Secure storage if required
4. **Audit Trail**: Maintain processing logs

### **👨‍⚕️ Clinical Documentation Standards**

**Chief Complaint (CC)**
- Brief, patient's own words
- Primary reason for visit
- Example: "Chest pain for 3 days"

**History of Present Illness (HPI)**
- Detailed symptom description
- Onset, duration, severity, triggers
- Associated symptoms

**Past Medical History (PMH)**
- Previous diagnoses
- Surgeries and procedures
- Hospitalizations

**Medications**
- Current prescriptions
- Dosages and frequencies
- Over-the-counter medications

**Allergies**
- Drug allergies with reactions
- Environmental allergies
- Food allergies if relevant

**Social History**
- Smoking, alcohol, drug use
- Occupation and environment
- Living situation

**Family History**
- Relevant hereditary conditions
- Age of relatives and causes of death
- Genetic risk factors

**Vital Signs**
- Blood pressure, heart rate
- Temperature, respiratory rate
- Oxygen saturation, weight

**Physical Examination**
- General appearance
- System-specific findings
- Abnormalities noted

**Assessment**
- Clinical impression
- Differential diagnosis
- Problem list

**Plan**
- Treatment recommendations
- Medications prescribed
- Follow-up instructions
- Tests ordered

---

## 🔍 **ADVANCED SEARCH & CODING**

### **🏷️ Medical Code Search Strategies**

#### **ICD-10 Diagnosis Codes**
```bash
# Symptom-based searches
curl "http://localhost:7717/api/v1/medical-codes/icd/search?query=chest%20pain&limit=10"
curl "http://localhost:7717/api/v1/medical-codes/icd/search?query=shortness%20breath&limit=10"
curl "http://localhost:7717/api/v1/medical-codes/icd/search?query=headache&limit=10"

# Condition-based searches  
curl "http://localhost:7717/api/v1/medical-codes/icd/search?query=hypertension&limit=10"
curl "http://localhost:7717/api/v1/medical-codes/icd/search?query=diabetes&limit=10"
curl "http://localhost:7717/api/v1/medical-codes/icd/search?query=depression&limit=10"
```

#### **CPT Procedure Codes**
```bash
# Office visits
curl "http://localhost:7717/api/v1/medical-codes/cpt/search?query=office%20visit&limit=10"
curl "http://localhost:7717/api/v1/medical-codes/cpt/search?query=consultation&limit=10"

# Common procedures
curl "http://localhost:7717/api/v1/medical-codes/cpt/search?query=examination&limit=10"
curl "http://localhost:7717/api/v1/medical-codes/cpt/search?query=blood%20test&limit=10"
curl "http://localhost:7717/api/v1/medical-codes/cpt/search?query=x-ray&limit=10"
```

#### **SNOMED Clinical Concepts**
```bash
# Clinical findings
curl "http://localhost:7717/api/v1/medical-codes/snomed/search?query=chest%20pain&limit=5"
curl "http://localhost:7717/api/v1/medical-codes/snomed/search?query=ECG&limit=5"
```

### **📊 Code Confidence Interpretation**

| Confidence Score | Interpretation | Action |
|------------------|----------------|--------|
| **90-100%** | Exact match | ✅ Approve automatically |
| **70-89%** | Very good match | ✅ Review and approve |
| **60-69%** | Good match | ⚠️ Review carefully |
| **50-59%** | Possible match | ⚠️ Manual verification needed |
| **< 50%** | Poor match | ❌ Likely incorrect |

### **🔄 Medical Code Validation Process**

1. **Review Auto-Assigned Codes**: Check all codes with confidence scores
2. **Validate Clinical Relevance**: Ensure codes match patient condition
3. **Check Code Hierarchy**: Verify most specific codes are used
4. **Cross-Reference Guidelines**: Follow coding best practices
5. **Document Rationale**: Note any manual overrides

---

## 🚨 **COMPREHENSIVE TROUBLESHOOTING**

### **🔧 System Startup Issues**

**❌ Python/Dependencies**
```bash
# Issue: Python not found
Solution: Install Python 3.10+ from python.org

# Issue: Module not found
Solution: Activate virtual environment and reinstall
venv\Scripts\activate
pip install -r requirements.txt

# Issue: Port already in use
Solution: Change port in main.py or kill existing process
netstat -ano | findstr :7717
taskkill /PID <process_id> /F
```

**❌ AnythingLLM Connection**
```bash
# Issue: Connection refused
curl http://localhost:3001/api/v1/auth -H "Authorization: Bearer 2ZKN48Y-F1M4D6T-GBX3F4K-DQFMEP7"

# Solutions:
1. Start AnythingLLM server: cd ../simple-npu-chatbot-main && npm start
2. Check API key in config.yaml
3. Verify port 3001 is not blocked
4. Test with curl command above
```

**❌ Database Issues**
```bash
# Issue: Database corruption
Solution: Delete feedvox.db and restart (will recreate)
rm feedvox.db
python main.py

# Issue: Medical codes not imported
Solution: Check CSV files and restart
ls "mecial codes/"  # Should show ICD-10.csv, CPT.csv, SNOMED-CT.csv
```

### **📤 Upload & Processing Issues**

**❌ Audio Upload Failures**
| Error | Cause | Solution |
|-------|-------|----------|
| "No file selected" | Postman form-data issue | Click "Select Files", don't type path |
| "Unsupported format" | Wrong file type | Convert to WAV, MP3, or M4A |
| "File too large" | Size > 100MB | Compress or split audio |
| "Upload timeout" | Network/size issue | Check connection, try smaller file |
| "Processing failed" | Audio corruption | Try different audio file |

**❌ Transcription Errors**
| Error | Cause | Solution |
|-------|-------|----------|
| "Whisper model failed" | Model loading issue | Restart server, check disk space |
| "Audio too short" | < 1 second audio | Use longer audio files |
| "No speech detected" | Silent/noisy audio | Use clear speech recordings |
| "Processing timeout" | Very long audio | Split into 30-minute segments |
| "Memory error" | Insufficient RAM | Close other applications |

**❌ Medical Note Extraction Issues**
| Error | Cause | Solution |
|-------|-------|----------|
| "LLM connection failed" | AnythingLLM down | Restart AnythingLLM server |
| "Empty response" | Poor transcript | Use clear medical conversation |
| "Parsing failed" | LLM response format | Retry extraction |
| "Timeout" | Long processing | Wait longer or restart |
| "Authentication failed" | Wrong API key | Check config.yaml |

**❌ Medical Coding Issues**
| Error | Cause | Solution |
|-------|-------|----------|
| "No codes found" | Empty medical note | Ensure proper medical conversation |
| "Code assignment failed" | Database error | Check database permissions |
| "Low confidence scores" | Poor matches | Review and manually assign |
| "Missing code types" | Limited database | Verify CSV imports |

### **🔍 Advanced Diagnostics**

**Check System Status**
```bash
# Health check
curl http://localhost:7717/health

# System status
curl http://localhost:7717/status

# Medical codes statistics
curl http://localhost:7717/api/v1/medical-codes/stats
```

**Log Analysis**
- **Server logs**: Check console output for errors
- **Database logs**: Look for SQLite connection issues
- **Whisper logs**: Monitor transcription processing
- **LLM logs**: Check AnythingLLM communication

**Performance Monitoring**
- **CPU usage**: Monitor during transcription
- **Memory usage**: Watch for memory leaks
- **Disk space**: Ensure adequate storage
- **Network**: Check AnythingLLM connectivity

---

## 📊 **PERFORMANCE OPTIMIZATION**

### **🚀 Speed Optimization**

**Audio Processing**
- Use WAV format for fastest processing
- Keep files under 30 minutes
- Record in 16kHz mono for efficiency
- Pre-process to remove silence

**Medical Note Extraction**
- Ensure AnythingLLM is NPU-accelerated
- Use shorter, focused transcripts
- Avoid very noisy transcriptions

**Database Performance**
- Regular database maintenance
- Monitor table sizes
- Index optimization for searches

### **💾 Storage Management**

**Database Size**
- Monitor `feedvox.db` growth
- Archive old records periodically
- Compress historical data

**Audio Files**
- Don't store original audio permanently
- Use compression for archives
- Implement retention policies

**Backup Strategy**
- Regular database backups
- Export medical notes to JSON
- Version control configurations

---

## 🔗 **INTEGRATION PROCEDURES**

### **🏥 EHR Integration**

**API Integration Points**
1. **POST** `/api/v1/transcription/upload` - Audio submission
2. **POST** `/api/v1/notes/extract` - Note extraction
3. **GET** `/api/v1/notes/{id}` - Retrieve complete record
4. **GET** `/api/v1/medical-codes/search` - Code validation

**Data Export Formats**
- JSON for API integration
- HL7 FHIR compliance ready
- CSV for bulk exports
- XML for legacy systems

**Authentication & Security**
- API key authentication
- HTTPS enforcement
- Data encryption at rest
- Audit logging

### **📋 Practice Management Integration**

**Workflow Integration**
1. **Schedule**: Link audio recording to appointments
2. **Record**: Automatic audio capture during visits
3. **Process**: Real-time transcription and coding
4. **Review**: Clinician validation workflow
5. **Bill**: Export codes for billing systems
6. **Archive**: Long-term storage management

**Custom API Endpoints**
- Batch processing capabilities
- Webhook notifications
- Custom field mapping
- Role-based access control

---

## 📈 **QUALITY ASSURANCE PROCEDURES**

### **✅ Validation Checklists**

**Audio Quality Checklist**
- [ ] Clear speech, minimal background noise
- [ ] Complete conversation captured
- [ ] Appropriate file format
- [ ] Reasonable file size
- [ ] No audio corruption

**Transcription Quality Checklist**
- [ ] Accurate speech-to-text conversion
- [ ] Medical terminology correctly transcribed
- [ ] Speaker identification clear
- [ ] Complete conversation captured
- [ ] Minimal transcription errors

**Medical Note Quality Checklist**
- [ ] All 11 sections populated appropriately
- [ ] Clinical information accurate
- [ ] Proper medical terminology used
- [ ] Logical flow and structure
- [ ] Complete documentation

**Medical Coding Quality Checklist**
- [ ] Codes relevant to patient condition
- [ ] Appropriate confidence scores (60%+)
- [ ] ICD-10 codes for all diagnoses
- [ ] CPT codes for all procedures
- [ ] No duplicate or conflicting codes

### **🎯 Quality Metrics**

**Target Performance Metrics**
- **Transcription Accuracy**: > 95%
- **Note Completion Rate**: > 90%
- **Code Assignment Rate**: > 85%
- **Processing Time**: < 5 minutes total
- **System Uptime**: > 99%

**Monitoring Procedures**
- Regular accuracy spot checks
- Performance metric tracking
- User feedback collection
- Error rate monitoring
- Continuous improvement process

---

## 🎓 **TRAINING & BEST PRACTICES**

### **👨‍⚕️ Clinical Staff Training**

**Basic Training (2 hours)**
1. System overview and capabilities
2. Audio recording best practices
3. Using Postman collection
4. Reviewing extracted notes
5. Validating medical codes

**Advanced Training (4 hours)**
1. Custom workflow setup
2. API integration concepts
3. Quality assurance procedures
4. Troubleshooting common issues
5. Performance optimization

**Ongoing Training**
- Monthly system updates
- New feature demonstrations
- Best practice sharing
- Error case reviews

### **🔧 Technical Staff Training**

**System Administration (6 hours)**
1. Installation and configuration
2. Database management
3. Performance monitoring
4. Security implementation
5. Backup and recovery

**Integration Development (8 hours)**
1. API documentation review
2. Custom endpoint development
3. Authentication implementation
4. Data mapping procedures
5. Testing and validation

---

## 🎉 **SUCCESS METRICS & VALIDATION**

### **✅ System Validation Checklist**

**Complete System Test**
- [ ] Server starts without errors
- [ ] AnythingLLM connection successful
- [ ] Audio upload and transcription works
- [ ] Medical note extraction completes
- [ ] Medical codes assigned automatically
- [ ] Search endpoints functional
- [ ] Database operations successful

**Performance Validation**
- [ ] Transcription time < 1/3 audio duration
- [ ] Note extraction < 10 seconds
- [ ] Medical coding < 5 seconds
- [ ] Total workflow < 5 minutes
- [ ] API response times < 2 seconds

**Quality Validation**
- [ ] Transcription accuracy > 95%
- [ ] Note fields > 90% populated
- [ ] Medical codes > 85% relevant
- [ ] Confidence scores > 60%
- [ ] No critical errors in processing

### **🏆 Success Indicators**

When FeedVox AI is working optimally:

✅ **Audio Processing**: Clear, accurate transcriptions in reasonable time  
✅ **Medical Notes**: Complete, structured clinical documentation  
✅ **Medical Coding**: Relevant ICD-10, CPT, SNOMED codes assigned  
✅ **System Performance**: Fast, reliable processing  
✅ **Integration Ready**: API endpoints functional and documented  
✅ **Quality Assurance**: Validation procedures in place  
✅ **User Adoption**: Clinical staff effectively using system  

---

**🏥 FeedVox AI is ready for production medical documentation workflows!** 