// This file is part of File Collection Manager
// Copyright (C) 2009 Brian Allen Vanderburg II
//
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 3 of the License, or
// (at your option) any later version.


// Requirements
#include <cassert>
#include <vector>

#include <wx/defs.h>
#include <wx/arrstr.h>
#include <wx/choicdlg.h>
#include <wx/dir.h>
#include <wx/file.h>
#include <wx/filename.h>
#include <wx/intl.h>
#include <wx/log.h>
#include <wx/progdlg.h>
#include <wx/string.h>

#include "actions.h"
#include "checksum.h"
#include "log.h"

#include "collection/collection.h"


// Action callback
//----------------------------------------------------------------------------

// Constructor
ActionCallback::ActionCallback(wxWindow* parent, Log* log, const wxString& title) :
    m_parent(parent),
    m_log(log),
    m_title(title),
    m_progress(NULL),
    m_continue(true),
    m_skip(0),
    m_counter(0)
{
    Resume();
}

// Destructor
ActionCallback::~ActionCallback()
{
    Suspend();
}

// Update progress message
bool ActionCallback::Progress(const wxString& message)
{
    if(m_progress)
    {
        m_counter++;
        if(m_counter > m_skip)
        {
            m_continue = m_progress->Pulse(message);
            m_counter = 0;
        }
    }

    return m_continue;
}

// Log a message
void ActionCallback::LogMessage(const wxString& message, bool important)
{
    if(m_log && m_progress) // m_progress is NULL when suspended
        m_log->LogMessage(message, important);
}

// Set skip counter for proress updates
void ActionCallback::SetProgressSkip(int skip)
{
    m_skip = skip;

    if(m_skip < 0)
        m_skip = 0;

    if(m_counter > m_skip)
        m_counter = m_skip;
}

// Suspend the callback
void ActionCallback::Suspend()
{
    if(m_progress)
    {
        m_progress->Destroy();
        m_progress = NULL;
    }
}

// Resume the callback
void ActionCallback::Resume()
{
    if(!m_progress)
    {
        m_progress = new wxProgressDialog(m_title, wxEmptyString, 100, m_parent,
            wxPD_APP_MODAL | wxPD_SMOOTH | wxPD_CAN_ABORT);
    }
}


// Private helper classes and methods
//----------------------------------------------------------------------------
namespace
{

// Rename candidate
struct RenameCandidate
{
    RenameCandidate(Node* _node, const wxString& _name) : 
        node(_node), name(_name)
    {
    }

    Node* node;
    wxString name;
};

typedef std::vector<RenameCandidate> RenameCandidateList;

// Rename item finder for finding renamed items
class RenameItemFinder : public wxDirTraverser
{
public:
    // ctor
    RenameItemFinder(Node* node) :
        m_node(node),
        m_len(0)
    {
        m_name = node->GetName();
        if(dynamic_cast<Directory*>(node))
        {
            m_dir = true;
        }
        else
        {
            m_dir = false;
        }
    }

    // on file
    wxDirTraverseResult OnFile(const wxString& filename)
    {
        if(!m_dir)
        {
            wxFileName fn(filename);
            wxString name = fn.GetFullName();

            AddIfGood(name);
        }

        return wxDIR_CONTINUE;
    }

    // on dir
    wxDirTraverseResult OnDir(const wxString& dirname)
    {
        if(m_dir)
        {
            wxFileName fn(dirname, wxEmptyString);
            wxString name = fn.GetDirs().Last();

            AddIfGood(name);
        }

        return wxDIR_IGNORE; // don't recurse
    }

    // Update external list
    void Update(RenameCandidateList& candidates)
    {
        candidates.insert(candidates.end(), m_candidates.begin(), m_candidates.end());
    }

private:
    // match length
    size_t GetMatchLength(const wxString& name)
    {
        size_t len = m_name.Len();
        if(name.Len() < len)
            len = name.Len();

        size_t pos;
        for(pos = 0; pos < len; pos++)
        {
            if(name[pos] != m_name[pos])
                return pos;
        }

        return pos;
    }

    // Add candidate to list if it is good
    void AddIfGood(const wxString& name)
    {
        size_t matchLen = GetMatchLength(name);
        if(matchLen > 0)
        {
            if(matchLen > m_len)
            {
                m_candidates.clear();
                m_len = matchLen;
            }

            if(matchLen == m_len)
            {
                m_candidates.push_back(RenameCandidate(m_node, name));
            }
        }
    }

    Node* m_node;
    size_t m_len;
    wxString m_name;
    bool m_dir;
    RenameCandidateList m_candidates;
};


// Rename candidate search function
bool FindRenameCandidates(Directory* dir, ActionCallback& callback, RenameCandidateList& candidates)
{
    assert(dir);

    if(!dir->Exists())
        return true;

    NodeList items(dir->GetChildren());
    for(NodeList::iterator it = items.begin(), end = items.end(); it != end; ++it)
    {
        Node* node = *it;
        assert(node);

        wxString iname = node->GetFullName();
        if(!callback.Progress(iname))
            return false;

        if(node->Exists())
        {
            Directory* subdir = dynamic_cast<Directory*>(node);
            if(subdir)
            {
                if(!FindRenameCandidates(subdir, callback, candidates))
                    return false;
            }
            continue;
        }
    
        // Item does not exist, try to find a replacement
        wxDir dirContents(dir->GetFullPath());
        RenameItemFinder finder(node);

        dirContents.Traverse(finder);
        finder.Update(candidates);
    }

    return true;
}

// Find new items under a directory
class NewItemFinder : public wxDirTraverser
{
public:
    NewItemFinder(Directory* dir, ActionCallback& callback, bool add) : 
        m_dir(dir),
        m_callback(callback),
        m_add(add)
    {
    }

    wxDirTraverseResult OnFile(const wxString& filename)
    {
        // Don't add filename if it is the collection file
        Collection* collection = m_dir->GetCollection();
        if(collection)
        {
            if(filename == collection->GetFilename())
                return wxDIR_CONTINUE;
            if(filename == collection->GetBackupFilename())
                return wxDIR_CONTINUE;
        }

        wxFileName fn(filename);
        wxString name = fn.GetFullName();

        if(!m_callback.Progress(filename))
            return wxDIR_STOP;

        if(!m_dir->HasFile(name))
        {
            File* file = new File();
            file->Rename(name);

            wxString message = _("New File: ") + file->GetFullName(m_dir);
            m_callback.LogMessage(message, !m_add);
            if(m_add)
            {
                file->SetSize(file->GetRealSize());
                m_dir->AddChild(file);
            }
            else
            {
                file->Delete();
            }
        }

        return wxDIR_CONTINUE;
    }

    wxDirTraverseResult OnDir(const wxString& dirname)
    {
        wxFileName fn(dirname, wxEmptyString);
        wxString name = fn.GetDirs().Last();

        if(!m_callback.Progress(dirname))
            return wxDIR_STOP;

        if(!m_dir->HasDirectory(name))
        {
            Directory* dir = new Directory();
            dir->Rename(name);

            wxString message = _("New Directory: ") + dir->GetFullName(m_dir);
            m_callback.LogMessage(message, !m_add);
            if(m_add)
            {
                m_dir->AddChild(dir);
            }
            else
            {
                dir->Delete();
            }
        }

        return wxDIR_IGNORE; // don't recurse into directory
    }

private:
    Directory* m_dir;
    ActionCallback& m_callback;
    bool m_add;
};

// Find new items
bool FindNewItems(Directory* dir, ActionCallback& callback, bool add)
{
    assert(dir);
        
    if(!dir->Exists())
    {
        wxString message = _("Missing Directory: ") + dir->GetFullName();
        callback.LogMessage(message, true);
        return true;
    }

    // Scan directory
    wxDir dirObject(dir->GetFullPath());
    NewItemFinder finder(dir, callback, add);

    dirObject.Traverse(finder);

    // Now scan any subdirectories
    DirectoryList subdirs = dir->GetDirectories();
    for(DirectoryList::iterator it = subdirs.begin(), end = subdirs.end(); it != end; ++it)
    {
        Directory* subdir = *it;
        assert(subdir);

        wxString iname = subdir->GetFullName();
        if(!callback.Progress(iname))
            return false;

        if(!FindNewItems(subdir, callback, add))
            return false;
    }

    return true;
}

// Calculate checksums of a file
bool Calculate(File* fileobj, ActionCallback& callback, const wxString& type, wxString& checksum, wxMemoryBuffer& buffer)
{
    wxLogNull nolog;
    checksum = wxEmptyString;

    // Open file
    wxString iname = fileobj->GetFullName();
    wxString filename = fileobj->GetFullPath();
    wxFile file(filename);

    if(!file.IsOpened())
    {
        wxString message = wxString::Format(_("Open Failed: %s"), iname.c_str());
        callback.LogMessage(message, true);
        return true;
    }

    // Prepare checksum calculator
    ChecksumCalculator calculator(type);
    if(!calculator.IsOk())
    {
        wxString message = wxString::Format(_("Error Calculating Checksum: %s"), iname.c_str());
        callback.LogMessage(message, true);
        return true;
    }

    // Calculate checksum
    const size_t bufSize = buffer.GetBufSize();
    void* cbuf = static_cast<void*>(buffer.GetData());

    while(!file.Eof())
    {
        if(!callback.Progress(iname))
            return false;

        size_t read = file.Read(cbuf, bufSize);
        calculator.Update(cbuf, read);
    }

    checksum = calculator.Finish();
    return true;
}

// Scan for missing items
bool FindMissingItems(Directory* dir, ActionCallback& callback)
{
    assert(dir);

    NodeList items(dir->GetChildren(true));
    items.push_front(dir);

    for(NodeList::iterator it = items.begin(), end = items.end(); it != end; ++it)
    {
        Node* node = *it;
        assert(node);

        wxString iname = node->GetFullName();
        if(!callback.Progress(iname))
            return false;

        if(!node->Exists())
        {
            wxString message;

            if(dynamic_cast<Directory*>(node))
            {
                message.Printf(_("Missing Directory: %s"), iname.c_str());
            }
            else
            {
                message.Printf(_("Missing File: %s"), iname.c_str());
            }

            callback.LogMessage(message, true);
        }
    }

    return true;
}

// Scan for items with wrong sizes
bool FindWrongSizes(Directory* dir, ActionCallback& callback)
{
    assert(dir);

    FileList files = dir->GetFiles(true);
    for(FileList::iterator it = files.begin(), end= files.end(); it != end; ++it)
    {
        File* file = *it;
        assert(file);

        wxString iname = file->GetFullName();
        if(!callback.Progress(iname))
            return false;

        wxString message;
        if(!file->Exists())
        {
            message = _("Missing File: ") + iname;
        }
        if(file->GetSize() == File::InvalidSize)
        {
            message = _("No Size Information: ") + iname;
        }
        else if(file->GetSize() != file->GetRealSize())
        {
            message = _("Mismatched Size: ") + iname;
        }

        if(message != wxEmptyString)
            callback.LogMessage(message, true);
    }

    return true;
}

// Scan for dirty items
bool FindDirtyFiles(Directory* dir, ActionCallback& callback)
{
    assert(dir);

    FileList files = dir->GetFiles(true);
    for(FileList::iterator it = files.begin(), end = files.end(); it != end; ++it)
    {
        File* file = *it;
        assert(file);

        wxString iname = file->GetFullName();
        if(!callback.Progress(iname))
            return false;

        if(file->IsDirty())
        {
            callback.LogMessage(_("Dirty File: ") + iname, true);
        }
    }

    return true;
}

// Scan for duplicate items
bool FindDuplicateItems(Directory* dir, ActionCallback& callback)
{
    assert(dir);

    wxArrayString once;
    wxArrayString twice;

    NodeList children = dir->GetChildren(true);
    children.push_front(dir);

    for(NodeList::iterator it = children.begin(), end = children.end(); it != end; ++it)
    {
        Node* node = *it;
        assert(node);

        wxString iname = node->GetFullName();
        if(!callback.Progress(iname))
            return false;

        if(once.Index(iname) == wxNOT_FOUND)
        {
            once.Add(iname);
        }
        else if(twice.Index(iname) == wxNOT_FOUND)
        {
            // Found it once already so it is a duplicate item
            twice.Add(iname);

            wxString message = _("Duplicate Item: ") + iname;
            callback.LogMessage(message, true);
        }
    }
    return true;
}

// Check dependencies
bool CheckDependencies(Directory* dir, ActionCallback& callback)
{
    assert(dir);

    Collection* collection = dir->GetCollection();
    if(!collection)
        return false;

    // Get all packages
    PackageList packages;

    FileList children = collection->GetFiles(true);
    FileList::iterator it, end;
    for(it = children.begin(), end = children.end(); it != end; ++it)
    {
        File* file = *it;
        wxString iname = file->GetFullName();

        if(!callback.Progress(iname))
            return false;

        PackageList filePackages = file->GetPackages();
        packages.insert(packages.end(), filePackages.begin(), filePackages.end());
    }

    // Scan dependencies
    children = dir->GetFiles(true);
    for(it = children.begin(), end = children.end(); it != end; ++it)
    {
        File* file = *it;
        assert(file);

        wxString iname = file->GetFullName();
        if(!callback.Progress(iname))
            return false;

        DependencyList deps = file->GetDependencies();
        for(DependencyList::iterator it2 = deps.begin(), end2 = deps.end(); it2 != end2; ++it2)
        {
            Dependency* dep = *it2;
            assert(dep);

            bool found = false;
            for(PackageList::iterator it3 = packages.begin(), end3 = packages.end(); it3 != end3; ++it3)
            {
                Package* pkg = *it3;
                assert(pkg);

                if(dep->Check(pkg))
                {
                    found = true;
                    break;
                }
            }

            if(!found)
            {
                wxString message = wxString::Format(_("Dependency Missing (%s): %s"),
                    dep->GetDisplayString().c_str(), iname.c_str());
                callback.LogMessage(message, true);
            }
        }
    }

    return true;
}

} // private namespace


// Verify sanity
bool VerifySanity(Directory* dir, ActionCallback& callback)
{
    assert(dir);

    const wxChar separator[] = wxT("-----------------------------------------------------------");

    callback.LogMessage(_("Checking for missing items."));
    callback.LogMessage(separator);
    if(!FindMissingItems(dir, callback))
        return false;

    callback.LogMessage(_("Checking for wrong sizes."));
    callback.LogMessage(separator);
    if(!FindWrongSizes(dir, callback))
        return false;

    callback.LogMessage(_("Checking for dirty items."));
    callback.LogMessage(separator);
    if(!FindDirtyFiles(dir, callback))
        return false;
    
    callback.LogMessage(_("Checking for new items."));
    callback.LogMessage(separator);
    if(!FindNewItems(dir, callback, false))
        return false;
    
    callback.LogMessage(_("Checking for duplicate items."));
    callback.LogMessage(separator);
    if(!FindDuplicateItems(dir, callback))
        return false;

    callback.LogMessage(_("Checking dependencies."));
    callback.LogMessage(separator);
    if(!CheckDependencies(dir, callback))
        return false;

    return true;
}

// Add new items
bool AddNewItems(Directory* dir, ActionCallback& callback)
{
    return FindNewItems(dir, callback, true);
}

// Attempt rename of missing items
bool RenameMissingItems(Directory* dir, ActionCallback& callback)
{
    assert(dir);

    // Find candidates
    RenameCandidateList candidates;
    if(!FindRenameCandidates(dir, callback, candidates))
        return false;

    if(candidates.size() == 0)
        return true;

    // Prompt user
    callback.Suspend();

    wxArrayString choices;
    for(RenameCandidateList::iterator it = candidates.begin(), end = candidates.end(); it != end; ++it)
    {
        choices.Add(it->node->GetFullName() + wxT("\n") + it->node->GetFullName(NULL, it->name));
    }

    wxArrayInt selected;
    size_t count = ::wxGetMultipleChoices(selected, _("Select items to rename"), _("Rename"),
        choices, callback.GetParent());
    if(count == 0)
        return true;

    // Rename the selected items
    callback.Resume();
    for(size_t pos = 0; pos < count; ++pos)
    {
        int index = selected[pos];

        Node* node = candidates[index].node;
        wxString name = candidates[index].name;

        wxString original = node->GetFullName();
        if(node->Rename(name))
        {
            callback.LogMessage(original + wxT(" >>> ") + name);
        }
        else
        {
            callback.LogMessage(_("Rename Error: ") + node->GetFullName());
        }
    }

    return true;
}

// Remove missing items
bool RemoveMissingItems(Directory* dir, ActionCallback& callback)
{
    assert(dir);

    NodeList children = dir->GetChildren();
    for(NodeList::iterator it = children.begin(), end = children.end(); it != end; ++it)
    {
        Node* node = *it;
        assert(node);

        wxString iname = node->GetFullName();
        if(!callback.Progress(iname))
            return false;

        if(!node->Exists())
        {
            wxString message = _("Removed: ") + iname;
            if(node->Delete())
                callback.LogMessage(message);
        }
        else if(dynamic_cast<Directory*>(node))
        {
            if(!RemoveMissingItems(dynamic_cast<Directory*>(node), callback))
                return false;
        }
    }

    return true;
}

// Calculate checksums
bool CalculateChecksums(const FileList& files, ActionCallback& callback, const wxString& type, bool all)
{
    if(!ChecksumCalculator::Exists(type))
    {
        wxString message = wxString::Format(_("Unknown Checksum Type: %s"), type.c_str());
        callback.LogMessage(message, true);
        return false;
    }

    wxMemoryBuffer buffer(1024 * 1024);
    for(FileList::const_iterator it = files.begin(), end = files.end(); it != end; ++it)
    {
        File* file = *it;
        assert(file);

        wxString iname = file->GetFullName();
        if(!callback.Progress(iname))
            return false;

        if(!file->Exists())
        {
            wxString message = _("Missing File: ") + iname;
            callback.LogMessage(message, true);
            continue;
        }

        // Determine whether to calculate or not
        if(all || file->GetChecksum() == wxEmptyString || file->GetSize() != file->GetRealSize())
        {
            // Calculate and record
            wxString checksum;
            if(!Calculate(file, callback, type, checksum, buffer))
                return false;

            if(checksum != wxEmptyString)
            {
                file->SetChecksum(checksum);
                file->SetSize(file->GetRealSize());

                wxString message = wxString::Format(_("Checksum Calculated (%s): %s"), checksum.c_str(), iname.c_str());
                callback.LogMessage(message);
            }
        }
    }

    return true;
}

bool CalculateChecksums(Directory* dir, ActionCallback& callback, const wxString& type, bool all)
{
    assert(dir);

    FileList files = dir->GetFiles(true);
    return CalculateChecksums(files, callback, type, all);
}

// Verify checksums
bool VerifyChecksums(const FileList& files, ActionCallback& callback)
{
    wxMemoryBuffer buffer(1024 * 1024);
    for(FileList::const_iterator it = files.begin(), end = files.end(); it != end; ++it)
    {
        File* file = *it;
        assert(file);

        wxString iname = file->GetFullName();
        if(!callback.Progress(iname))
            return false;

        if(!file->Exists())
        {
            wxString message = _("Missing File: ") + iname;
            callback.LogMessage(message, true);
            continue;
        }

        wxString checksum = file->GetChecksum();
        if(checksum == wxEmptyString)
        {
            wxString message = _("Missing Checksum: ") + iname;
            callback.LogMessage(message, true);
            continue;
        }

        wxString calculated;
        if(!Calculate(file, callback, checksum, calculated, buffer))
            return false;

        if(checksum.Upper() != calculated.Upper())
        {
            wxString message = _("Invalid Checksum: ") + iname;
            callback.LogMessage(message, true);
            continue;
        }
    }

    return true;
}

bool VerifyChecksums(Directory* dir, ActionCallback& callback)
{
    assert(dir);

    FileList files = dir->GetFiles(true);
    return VerifyChecksums(files, callback);
}

// Mark clean or dirty
bool MarkDirty(const FileList& files, ActionCallback& callback, bool dirty)
{
    for(FileList::const_iterator it = files.begin(), end = files.end(); it != end; ++it)
    {
        File* file = *it;
        assert(file);

        wxString iname = file->GetFullName();
        if(!callback.Progress(iname))
            return false;

        file->MarkDirty(dirty);
    }
    return true;
}

bool MarkDirty(Directory* dir, ActionCallback& callback, bool dirty)
{
    assert(dir);
    FileList files = dir->GetFiles(true);
    return MarkDirty(files, callback, dirty);
}

