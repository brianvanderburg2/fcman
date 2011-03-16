// This file is part of File Collection Manager
// Copyright (C) 2009 Brian Allen Vanderburg II
//
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 3 of the License, or
// (at your option) any later version.


// Requirements
#include <wx/defs.h>
#include <wx/filename.h>
#include <wx/xml/xml.h>
#include <wx/log.h>

#include "file.h"
#include "collection.h"


// Constructor
File::File() : m_size(File::InvalidSize), m_dirty(true)
{
}

// Construct from xml
File::File(wxXmlNode* node) : m_size(File::InvalidSize), m_dirty(true)
{
    m_name = node->GetPropVal(wxT("name"), wxT("untitled"));
    m_checksum = node->GetPropVal(wxT("checksum"), wxEmptyString);

    wxString sizeStr = node->GetPropVal(wxT("size"), wxEmptyString);
    if(sizeStr != wxEmptyString)
    {
        // TODO: Currently only long supported instead of 64 bit longlong
        // It seems to be a problem in wxWidgets
        unsigned long size = 0;
        if(sizeStr.ToULong(&size))
        {
            m_size = size;
        }
    }

    wxString dirtyStr = node->GetPropVal(wxT("dirty"), wxEmptyString);
    if(dirtyStr.IsSameAs(wxT("yes"), false) || dirtyStr.IsSameAs(wxT("true"), false))
    {
        m_dirty = true;
    }
    else if(dirtyStr.IsSameAs(wxT("no"), false) || dirtyStr.IsSameAs(wxT("false"), false))
    {
        m_dirty = false;
    }

    wxXmlNode* child = node->GetChildren();
    while(child)
    {
        if(child->GetType() != wxXML_ELEMENT_NODE)
        {
            child = child->GetNext();
            continue;
        }

        if (child->GetName() == wxT("description"))
        {
            m_description = child->GetNodeContent();
        }
        else if(child->GetName() == wxT("package"))
        {
            Package* p = new Package(child);
            AddPackage(p);
        }
        else if(child->GetName() == wxT("dependency"))
        {
            Dependency* d = new Dependency(child);
            AddDependency(d);
        }

        child = child->GetNext();
    }
}

// Destructor
File::~File()
{
    while(m_packages.size() > 0)
    {
        delete m_packages.front();
    }

    while(m_dependencies.size() > 0)
    {
        delete m_dependencies.front();
    }
}

// Save to an XML node
wxXmlNode* File::Save()
{
    wxXmlNode* node = new wxXmlNode(NULL, wxXML_ELEMENT_NODE, wxT("file"));
    node->AddProperty(wxT("name"), m_name);

    if(m_checksum != wxEmptyString)
        node->AddProperty(wxT("checksum"), m_checksum);

    if(m_size != InvalidSize)
    {
        wxString sizeStr;
        sizeStr << static_cast<unsigned long>(m_size); // TODO: see todo in load code
        node->AddProperty(wxT("size"), sizeStr);
    }

    node->AddProperty(wxT("dirty"), m_dirty ? wxT("yes") : wxT("no"));

    if(m_description != wxEmptyString)
    {
        wxXmlNode* descNode = new wxXmlNode(node, wxXML_ELEMENT_NODE, wxT("description"));
        new wxXmlNode(descNode, wxXML_TEXT_NODE, wxEmptyString, m_description);
    }

    PackageList packages = GetPackages();
    for(PackageList::iterator it = packages.begin(), end = packages.end(); it != end; ++it)
    {
        wxXmlNode* child = (*it)->Save();
        node->AddChild(child);
    }

    DependencyList depends = GetDependencies();
    for(DependencyList::iterator it = depends.begin(), end = depends.end(); it != end; ++it)
    {
        wxXmlNode* child = (*it)->Save();
        node->AddChild(child);
    }
    return node;
}

// Determine existence
bool File::Exists() const
{
    if(!m_collection)
        return false;

    return wxFileName::FileExists(GetFullPath());
}

// Set checksum
void File::SetChecksum(const wxString& checksum)
{
    if(m_checksum != checksum)
    {
        m_checksum = checksum;
        m_dirty = true;

        if(m_collection)
            m_collection->SetDirty();
    }
}

// Set the size
void File::SetSize(wxULongLong_t size)
{
    if(size != m_size)
    {
        m_size = size;

        if(m_collection)
            m_collection->SetDirty();
    }
}

// Set the description
void File::SetDescription(const wxString& description)
{
    if(description != m_description)
    {
        m_description = description.Strip(wxString::both);

        if(m_collection)
            m_collection->SetDirty();
    }
}

// Get the real size
wxULongLong_t File::GetRealSize() const
{
    if(!Exists())
        return InvalidSize;

    wxULongLong result = wxFileName::GetSize(GetFullPath());
    if(result == wxInvalidSize)
        return InvalidSize;
    return result.GetValue();
}

// Invalid size (max unsigned 64 bit value)
const wxULongLong_t File::InvalidSize = wxULL(18446744073709551615);

// Add a package
void File::AddPackage(Package* package)
{
    if(package->m_file == this)
        return;

    if(package->m_file != NULL)
        package->m_file->RemovePackage(package);

    m_packages.push_back(package);
    package->m_file = this;

    if(m_collection)
        m_collection->SetDirty();
}

// Remove a package
void File::RemovePackage(Package* package)
{
    if(package->m_file != this)
        return;

    m_packages.remove(package);
    package->m_file = NULL;

    if(m_collection)
        m_collection->SetDirty();
}

// Get children
static bool package_sort(Package* p1, Package* p2)
{
    const wxString& name1 = p1->GetName();
    const wxString& name2 = p2->GetName();

    return name1.Cmp(name2) < 0;
}

PackageList File::GetPackages()
{
    PackageList packages(m_packages);
    packages.sort(package_sort);

    return packages;
}

// Add a dependency
void File::AddDependency(Dependency* depends)
{
    if(depends->m_file == this)
        return;

    if(depends->m_file != NULL)
        depends->m_file->RemoveDependency(depends);

    m_dependencies.push_back(depends);
    depends->m_file = this;

    if(m_collection)
        m_collection->SetDirty();
}

// Remove a dependency
void File::RemoveDependency(Dependency* depends)
{
    if(depends->m_file != this)
        return;

    m_dependencies.remove(depends);
    depends->m_file = NULL;

    if(m_collection)
        m_collection->SetDirty();
}

// Dirty flag
void File::MarkDirty(bool dirty)
{
    if(m_dirty != dirty)
    {
        m_dirty = dirty;

        if(m_collection)
            m_collection->SetDirty();
    }
}

// Get children
static bool dependency_sort(Dependency* d1, Dependency* d2)
{
    const wxString& name1 = d1->GetName();
    const wxString& name2 = d2->GetName();

    return name1.Cmp(name2) < 0;
}

DependencyList File::GetDependencies()
{
    DependencyList dependencies(m_dependencies);
    dependencies.sort(dependency_sort);

    return dependencies;
}

